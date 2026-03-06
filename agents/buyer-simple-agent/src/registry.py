"""Thread-safe in-memory seller registry.

Stores seller agent cards and payment info discovered via A2A registration,
manual discovery, or the Nevermined Discovery API (economy sellers).
"""

import threading
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class SellerInfo:
    """Parsed seller information from an agent card."""

    url: str
    name: str
    description: str
    skills: list[dict]
    plan_id: str = ""
    agent_id: str = ""
    credits: int = 1
    cost_description: str = ""


class SellerRegistry:
    """Thread-safe in-memory registry of seller agents."""

    def __init__(self):
        self._sellers: dict[str, SellerInfo] = {}
        self._lock = threading.Lock()

    def register(self, agent_url: str, agent_card: dict) -> SellerInfo:
        """Parse an agent card and store seller info.

        Args:
            agent_url: The seller's base URL.
            agent_card: The full agent card dict (from /.well-known/agent.json).

        Returns:
            The stored SellerInfo.
        """
        url = agent_url.rstrip("/")

        name = agent_card.get("name", "Unknown Agent")
        description = agent_card.get("description", "")
        skills = agent_card.get("skills", [])

        # Extract payment extension
        plan_id = ""
        agent_id = ""
        credits = 1
        cost_description = ""

        extensions = agent_card.get("capabilities", {}).get("extensions", [])
        for ext in extensions:
            if ext.get("uri") == "urn:nevermined:payment":
                params = ext.get("params", {})
                plan_id = params.get("planId", "")
                agent_id = params.get("agentId", "")
                credits = params.get("credits", 1)
                cost_description = params.get("costDescription", "")
                break

        info = SellerInfo(
            url=url,
            name=name,
            description=description,
            skills=skills,
            plan_id=plan_id,
            agent_id=agent_id,
            credits=credits,
            cost_description=cost_description,
        )

        with self._lock:
            self._sellers[url] = info

        return info

    def _base_url_from_endpoint(self, endpoint_url: str) -> str | None:
        """Derive base URL from Discovery endpointUrl. None if not a full URL."""
        if not endpoint_url or not endpoint_url.strip().startswith(("http://", "https://")):
            return None
        parsed = urlparse(endpoint_url.strip())
        if not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    def register_from_economy(self, seller: dict) -> "SellerInfo | None":
        """Register a seller from the Discovery API response.

        Only registers if seller has planIds and a callable endpointUrl.
        They then appear in list_all and can be used for purchase_a2a.

        Args:
            seller: One entry from Discovery API sellers[] (name, planIds,
                    nvmAgentId, endpointUrl, pricing, description, etc.).

        Returns:
            The stored SellerInfo, or None if missing planIds or base URL.
        """
        plan_ids = seller.get("planIds") or []
        if not plan_ids:
            return None
        endpoint_url = seller.get("endpointUrl", "")
        url = self._base_url_from_endpoint(endpoint_url)
        if not url:
            return None
        url = url.rstrip("/")
        name = seller.get("name", "Unknown")
        description = seller.get("description", "")
        services_sold = seller.get("servicesSold") or ""
        skills = [{"name": s.strip()} for s in services_sold.split(",") if s.strip()]
        plan_id = plan_ids[0]
        agent_id = seller.get("nvmAgentId", "")
        pricing = seller.get("pricing") or {}
        cost_description = pricing.get("perRequest") or str(pricing)
        info = SellerInfo(
            url=url,
            name=name,
            description=description,
            skills=skills,
            plan_id=plan_id,
            agent_id=agent_id,
            credits=1,
            cost_description=cost_description,
        )
        with self._lock:
            self._sellers[url] = info
        return info

    def get_payment_info(self, agent_url: str) -> dict | None:
        """Get cached payment info for a seller (skips re-discovery).

        Args:
            agent_url: The seller's base URL.

        Returns:
            Dict with planId, agentId, credits, or None if not registered.
        """
        url = agent_url.rstrip("/")
        with self._lock:
            info = self._sellers.get(url)
        if not info:
            return None
        return {
            "planId": info.plan_id,
            "agentId": info.agent_id,
            "credits": info.credits,
        }

    def list_all(self) -> list[dict]:
        """Return a summary list of all registered sellers."""
        with self._lock:
            sellers = list(self._sellers.values())
        result = []
        for s in sellers:
            skill_names = [
                sk.get("name", sk.get("id", "unknown")) for sk in s.skills
            ]
            result.append({
                "url": s.url,
                "name": s.name,
                "description": s.description,
                "skills": skill_names,
                "credits": s.credits,
                "cost_description": s.cost_description,
            })
        return result

    def get_first_url(self) -> str | None:
        """Return the URL of the first registered seller, or None."""
        with self._lock:
            if not self._sellers:
                return None
            return next(iter(self._sellers.values())).url

    def __len__(self) -> int:
        with self._lock:
            return len(self._sellers)
