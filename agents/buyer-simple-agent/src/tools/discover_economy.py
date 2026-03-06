"""Discover sellers from the Nevermined hackathon Discovery API.

Fetches GET https://nevermined.ai/hackathon/register/api/discover?side=sell
with x-nvm-api-key. Returns only sellers that have pricing and planIds set.
"""

from urllib.parse import urlparse

import httpx

from ..log import get_logger, log

DISCOVERY_BASE = "https://nevermined.ai/hackathon/register/api/discover"
_logger = get_logger("buyer.discovery")


def _base_url_from_endpoint(endpoint_url: str) -> str | None:
    """Derive base URL from Discovery endpointUrl. Returns None if not a full URL."""
    if not endpoint_url or not endpoint_url.strip().startswith(("http://", "https://")):
        return None
    parsed = urlparse(endpoint_url.strip())
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _has_pricing_and_plans(seller: dict) -> bool:
    """True if seller has at least pricing info and one planId."""
    pricing = seller.get("pricing")
    plan_ids = seller.get("planIds") or []
    return bool(pricing is not None and plan_ids)


def discover_economy_impl(
    nvm_api_key: str,
    side: str = "sell",
    category: str | None = None,
) -> dict:
    """Fetch sellers (and optionally buyers) from the Discovery API.

    Only includes sellers that have pricing and planIds set.

    Args:
        nvm_api_key: Nevermined API key (full value, e.g. sandbox:...).
        side: "sell" or "buy". Default "sell".
        category: Optional category filter (case-insensitive).

    Returns:
        dict with status, content (for Strands), sellers list, and meta.
    """
    try:
        params = {"side": side}
        if category:
            params["category"] = category
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                DISCOVERY_BASE,
                headers={"x-nvm-api-key": nvm_api_key},
                params=params,
            )
        if resp.status_code != 200:
            return {
                "status": "error",
                "content": [{"text": f"Discovery API returned HTTP {resp.status_code}"}],
                "sellers": [],
                "meta": {},
            }
        data = resp.json()
        meta = data.get("meta", {})
        raw_sellers = data.get("sellers", [])
        sellers = [s for s in raw_sellers if _has_pricing_and_plans(s)]
        log(_logger, "TOOLS", "DISCOVERY_ECONOMY",
            f"total={meta.get('total', 0)} with_pricing_planIds={len(sellers)}")
        if not sellers:
            return {
                "status": "success",
                "content": [{"text": "No economy sellers found with pricing and plan IDs set. "
                            "Try without a category filter, or try again later."}],
                "sellers": [],
                "meta": meta,
            }
        lines = [f"Economy sellers ({len(sellers)} with pricing and plans):"]
        for s in sellers:
            name = s.get("name", "Unknown")
            team = s.get("teamName", "")
            cat = s.get("category", "")
            pricing = (s.get("pricing") or {}).get("perRequest", "?")
            plans = s.get("planIds") or []
            endpoint = s.get("endpointUrl", "")
            base = _base_url_from_endpoint(endpoint)
            line = f"\n  • {name}"
            if team:
                line += f" ({team})"
            if cat:
                line += f" [{cat}]"
            line += f" — {pricing}"
            if base:
                line += f" — {base}"
            else:
                line += " — (no callable URL)"
            lines.append(line)
            if plans:
                lines.append(f"    planId: {plans[0][:24]}..." if len(plans[0]) > 24 else f"    planId: {plans[0]}")
        return {
            "status": "success",
            "content": [{"text": "\n".join(lines)}],
            "sellers": sellers,
            "meta": meta,
        }
    except httpx.RequestError as e:
        log(_logger, "TOOLS", "DISCOVERY_ECONOMY", f"request_error={e}")
        return {
            "status": "error",
            "content": [{"text": f"Cannot reach Discovery API: {e}"}],
            "sellers": [],
            "meta": {},
        }
    except Exception as e:
        log(_logger, "TOOLS", "DISCOVERY_ECONOMY", f"error={e}")
        return {
            "status": "error",
            "content": [{"text": f"Discovery failed: {e}"}],
            "sellers": [],
            "meta": {},
        }
