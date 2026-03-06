"""Discover sellers from the Nevermined hackathon Discovery API.

Fetches GET https://nevermined.ai/hackathon/register/api/discover?side=sell
with x-nvm-api-key. Returns all sellers from the API (no filtering).
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


def discover_economy_impl(
    nvm_api_key: str,
    side: str = "sell",
    category: str | None = None,
) -> dict:
    """Fetch sellers (and optionally buyers) from the Discovery API.

    Returns all sellers from the API; no filtering by pricing or planIds.

    Args:
        nvm_api_key: Nevermined API key (full value, e.g. sandbox:...).
        side: "sell" or "buy". Default "sell".
        category: Optional category filter (case-insensitive).

    Returns:
        dict with status, content (for Strands), sellers list, and meta.
    """
    try:
        params = {"side": side, "limit": 100}
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
        sellers = list(data.get("sellers", []))
        # Paginate if API returns hasMore/nextPage or total > len(sellers)
        api_total = meta.get("total")
        page = 1
        max_pages = 20
        while page < max_pages:
            if api_total is not None and len(sellers) >= api_total:
                break
            if len(sellers) < 100:
                break
            page += 1
            next_params = {**params, "page": page}
            resp = httpx.get(
                DISCOVERY_BASE,
                headers={"x-nvm-api-key": nvm_api_key},
                params=next_params,
                timeout=15.0,
            )
            if resp.status_code != 200:
                break
            next_data = resp.json()
            next_sellers = next_data.get("sellers", [])
            if not next_sellers:
                break
            sellers.extend(next_sellers)
            if not next_data.get("meta", {}).get("hasMore", True):
                break
        total = len(sellers)
        log(_logger, "TOOLS", "DISCOVERY_ECONOMY", f"total={total}")
        if not sellers:
            return {
                "status": "success",
                "content": [{"text": "No economy sellers returned. Try without a category filter, or try again later."}],
                "sellers": [],
                "meta": meta,
            }
        lines = [f"Economy sellers ({total}):"]
        for s in sellers:
            name = s.get("name", "Unknown")
            team = s.get("teamName", "")
            cat = s.get("category", "")
            pricing = (s.get("pricing") or {}).get("perRequest", "?")
            plans = s.get("planIds") or []
            plan_pricing = s.get("planPricing") or []
            plan_id = plans[0] if plans else (plan_pricing[0].get("planDid", "") if plan_pricing and isinstance(plan_pricing[0], dict) else "")
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
            if not plan_id:
                line += " [no planId]"
            lines.append(line)
            if plan_id:
                lines.append(f"    planId: {plan_id[:24]}..." if len(plan_id) > 24 else f"    planId: {plan_id}")
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
