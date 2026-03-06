"""
Strands agent definition with buyer tools for x402 data purchasing.

This is the heart of the buyer kit. Both agent.py (interactive CLI) and
agent_agentcore.py (AWS) import from here. The tools are plain @tool —
NOT @requires_payment — because the buyer generates tokens, not receives them.

Usage:
    from src.strands_agent import payments, create_agent, NVM_PLAN_ID, seller_registry
"""

import os

from dotenv import load_dotenv
from strands import Agent, tool

from payments_py import Payments, PaymentOptions

from .budget import Budget
from .log import get_logger, log
from .registry import SellerRegistry
from .tools.balance import check_balance_impl
from .tools.discover import discover_pricing_impl
from .tools.discover_a2a import discover_agent_impl
from .tools.discover_economy import discover_economy_impl
from .tools.purchase import purchase_data_impl
from .tools.purchase_a2a import purchase_a2a_impl
from .tools.purchase_rategenius import purchase_rategenius_impl

load_dotenv()


def _check_nvm_api_key() -> str:
    """Validate NVM_API_KEY and return it. Fail fast with a clear error if missing or placeholder."""
    key = os.environ.get("NVM_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "NVM_API_KEY is required. Set it in .env (see .env.example).\n"
            "Get your key from https://nevermined.app → API Keys → Global NVM API Keys."
        )
    if "your-" in key.lower() or key == "sandbox:" or key == "live:":
        raise SystemExit(
            "NVM_API_KEY looks like a placeholder. Replace it with your real key from\n"
            "https://nevermined.app → API Keys → Global NVM API Keys.\n"
            "Use a subscriber key for the buyer; format is sandbox:<key> or live:<key>."
        )
    # payments_py expects prefix:JWT (the part after ":" must be a JWT)
    if ":" in key:
        suffix = key.split(":", 1)[1]
        if suffix.count(".") < 2:
            raise SystemExit(
                "NVM_API_KEY is invalid: the part after 'sandbox:' or 'live:' must be a JWT.\n"
                "Copy the full key from https://nevermined.app → API Keys → Global NVM API Keys."
            )
    return key


NVM_API_KEY = _check_nvm_api_key()
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.getenv("NVM_AGENT_ID")
SELLER_URL = os.getenv("SELLER_URL", "http://localhost:3000")
SELLER_A2A_URL = os.getenv("SELLER_A2A_URL", "")

MAX_DAILY_SPEND = int(os.getenv("MAX_DAILY_SPEND", "0"))
MAX_PER_REQUEST = int(os.getenv("MAX_PER_REQUEST", "0"))

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)

budget = Budget(max_daily=MAX_DAILY_SPEND, max_per_request=MAX_PER_REQUEST)

_logger = get_logger("buyer.tools")

# Shared seller registry — used by tools and registration server
seller_registry = SellerRegistry()


# ---------------------------------------------------------------------------
# Buyer tools (plain @tool — no @requires_payment)
# ---------------------------------------------------------------------------

@tool
def discover_pricing(seller_url: str = "") -> dict:
    """Discover a seller's available data services and pricing tiers.

    Call this first to understand what data is available and how much it costs.

    Args:
        seller_url: Base URL of the seller (defaults to SELLER_URL env var).
    """
    url = seller_url or SELLER_URL
    return discover_pricing_impl(url)


@tool
def check_balance() -> dict:
    """Check your Nevermined credit balance and daily budget status.

    Returns your remaining credits on the seller's plan and your
    local spending budget status.
    """
    log(_logger, "TOOLS", "BALANCE", f"plan={NVM_PLAN_ID[:12]}")
    result = check_balance_impl(payments, NVM_PLAN_ID)
    budget_status = budget.get_status()
    result["budget"] = budget_status

    budget_lines = [
        "",
        "Local budget:",
        f"  Daily limit: {budget_status['daily_limit']}",
        f"  Daily spent: {budget_status['daily_spent']}",
        f"  Daily remaining: {budget_status['daily_remaining']}",
        f"  Total spent (session): {budget_status['total_spent']}",
    ]
    if result.get("content"):
        result["content"][0]["text"] += "\n".join(budget_lines)

    return result


@tool
def purchase_data(query: str, seller_url: str = "") -> dict:
    """Purchase data from a seller using x402 payment (FINAL STEP).

    Generates an x402 access token and sends the query to the seller.
    Budget limits are checked before purchasing.

    IMPORTANT: Call this tool AT MOST ONCE per user request. After it returns
    (success or error), stop calling tools and report the result to the user.

    Args:
        query: The data query to send to the seller.
        seller_url: Base URL of the seller (defaults to SELLER_URL env var).
    """
    url = seller_url or SELLER_URL

    # Pre-check with minimum 1 credit (actual cost is determined by the seller)
    allowed, reason = budget.can_spend(1)
    if not allowed:
        return {
            "status": "budget_exceeded",
            "content": [{"text": f"Budget check failed: {reason}"}],
            "credits_used": 0,
        }

    result = purchase_data_impl(
        payments=payments,
        plan_id=NVM_PLAN_ID,
        seller_url=url,
        query=query,
        agent_id=NVM_AGENT_ID,
    )

    credits_used = result.get("credits_used", 0)
    if result.get("status") == "success" and credits_used > 0:
        budget.record_purchase(credits_used, url, query)

    return result


# ---------------------------------------------------------------------------
# A2A buyer tools
# ---------------------------------------------------------------------------

@tool
def list_sellers() -> dict:
    """List all registered sellers, their skills, and pricing.

    Sellers register automatically via A2A when they start with --buyer-url.
    You can also register sellers manually with discover_agent.
    """
    sellers = seller_registry.list_all()
    log(_logger, "TOOLS", "LIST_SELLERS", f"count={len(sellers)}")
    if not sellers:
        return {
            "status": "success",
            "content": [{"text": "No sellers registered yet. "
                         "Sellers will appear here when they start with --buyer-url, "
                         "or you can discover one manually with discover_agent."}],
            "sellers": [],
        }

    lines = [f"Registered sellers ({len(sellers)}):"]
    for s in sellers:
        skills_str = ", ".join(s["skills"]) if s["skills"] else "none"
        lines.append(f"\n  {s['name']} ({s['url']})")
        lines.append(f"    Skills: {skills_str}")
        lines.append(f"    Min credits: {s['credits']}")
        if s["cost_description"]:
            lines.append(f"    Pricing: {s['cost_description']}")

    return {
        "status": "success",
        "content": [{"text": "\n".join(lines)}],
        "sellers": sellers,
    }


@tool
def discover_agent(agent_url: str = "") -> dict:
    """Discover a seller via A2A protocol by fetching its agent card.

    Retrieves /.well-known/agent.json from the seller and parses
    the payment extension to find plan ID, agent ID, and pricing.
    Also registers the seller in the local registry.

    Args:
        agent_url: Base URL of the A2A agent (defaults to SELLER_A2A_URL env var).
    """
    url = agent_url or SELLER_A2A_URL
    log(_logger, "TOOLS", "DISCOVER", f"url={url}")
    result = discover_agent_impl(url)

    if result.get("status") == "success":
        log(_logger, "TOOLS", "DISCOVER",
            f'found name={result.get("name", "?")} skills={len(result.get("skills", []))}')

        # Also register in the seller registry (best-effort)
        import httpx
        try:
            card_url = f"{url.rstrip('/')}/.well-known/agent-card.json"
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(card_url)
            if resp.status_code == 200:
                seller_registry.register(url, resp.json())
        except Exception:
            pass

    return result


@tool
def discover_economy_sellers(category: str = "") -> dict:
    """Discover sellers from the hackathon economy (Nevermined Discovery API).

    Fetches all sellers from the economy. Those with plan IDs and a callable URL
    are registered locally and appear in list_sellers for purchase_a2a.

    Args:
        category: Optional category filter (e.g. "Data Analytics", "AI/ML"). Leave empty for all.
    """
    result = discover_economy_impl(
        NVM_API_KEY,
        side="sell",
        category=category.strip() or None,
    )
    sellers = result.get("sellers", [])
    if result.get("status") == "success" and sellers:
        registered = 0
        for s in sellers:
            if seller_registry.register_from_economy(s):
                registered += 1
        log(_logger, "TOOLS", "DISCOVERY_ECONOMY", f"registered={registered}")
    return result


@tool
def search_marketplace(query: str, budget_max: float | None = None, top_k: int = 5) -> dict:
    """Search the AI marketplace for agents by description (RateGenius).

    Use this when the user wants to find agents that offer a specific service,
    e.g. \"social media sentiment analysis\", \"blockchain analytics\", \"grant writing\".
    RateGenius returns ranked agents with pricing and relevance. Costs 3 credits per search.

    Args:
        query: Plain-English description of the service you need.
        budget_max: Optional max price per request in USD (filters expensive agents).
        top_k: Max number of results to return (default 5).
    """
    allowed, reason = budget.can_spend(3)
    if not allowed:
        return {
            "status": "budget_exceeded",
            "content": [{"text": f"Budget check failed: {reason}"}],
            "credits_used": 0,
        }
    result = purchase_rategenius_impl(
        payments=payments,
        query=query,
        budget_max=budget_max,
        top_k=top_k,
    )
    credits_used = result.get("credits_used", 0)
    if result.get("status") == "success" and credits_used > 0:
        budget.record_purchase(credits_used, "RateGenius", query)
    return result


@tool
def purchase_a2a(query: str, agent_url: str = "") -> dict:
    """Purchase data from a seller using the A2A protocol (FINAL STEP).

    Sends an A2A message with automatic x402 payment via PaymentsClient.
    The agent card's payment extension provides the plan ID and agent ID.

    IMPORTANT: Call this tool AT MOST ONCE per user request. After it returns
    (success or error), stop calling tools and report the result to the user.

    If no agent_url is provided, uses the first registered seller from the
    registry, or falls back to SELLER_A2A_URL.

    Args:
        query: The data query to send to the seller.
        agent_url: Base URL of the A2A agent (optional if sellers are registered).
    """
    url = agent_url or SELLER_A2A_URL

    # If no URL specified, try the registry
    if not url:
        url = seller_registry.get_first_url()
    if not url:
        return {
            "status": "error",
            "content": [{"text": "No seller URL provided and no sellers registered. "
                         "Use list_sellers to check, or provide an agent_url."}],
            "credits_used": 0,
        }

    log(_logger, "TOOLS", "PURCHASE", f'url={url} query="{query[:60]}"')

    # Check registry for cached payment info (skip discovery round-trip)
    cached = seller_registry.get_payment_info(url)
    if cached:
        log(_logger, "TOOLS", "PURCHASE",
            f'using cached payment info plan={cached["planId"][:12]}')
        plan_id = cached["planId"] or NVM_PLAN_ID
        agent_id = cached["agentId"] or NVM_AGENT_ID or ""
        min_credits = cached["credits"]
    else:
        # Fall back to full discovery
        discovery = discover_agent_impl(url)
        if discovery.get("status") != "success":
            return {
                "status": "error",
                "content": [{"text": f"Cannot discover agent at {url}. Is it running?"}],
                "credits_used": 0,
            }
        payment = discovery.get("payment", {})
        plan_id = payment.get("planId", NVM_PLAN_ID)
        agent_id = payment.get("agentId", NVM_AGENT_ID or "")
        min_credits = payment.get("credits", 1)

    if not plan_id:
        return {
            "status": "error",
            "content": [{"text": "No plan ID found in agent card or environment."}],
            "credits_used": 0,
        }

    # Budget pre-check
    allowed, reason = budget.can_spend(min_credits)
    if not allowed:
        return {
            "status": "budget_exceeded",
            "content": [{"text": f"Budget check failed: {reason}"}],
            "credits_used": 0,
        }

    result = purchase_a2a_impl(
        payments=payments,
        plan_id=plan_id,
        agent_url=url,
        agent_id=agent_id,
        query=query,
    )

    credits_used = result.get("credits_used", 0)
    log(_logger, "TOOLS", "PURCHASE",
        f'status={result.get("status")} credits={credits_used}')
    if result.get("status") == "success" and credits_used > 0:
        budget.record_purchase(credits_used, url, query)

    return result


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

_GUIDELINES = """\

Important guidelines:
- Always discover the seller first so you can inform the user about costs.
- Check the balance before making a purchase to show the user their credit status.
- Even if the balance shows "not subscribed", you CAN still purchase. The x402
  payment flow handles subscription automatically during the verify/settle step.
- Tell the user the expected cost BEFORE purchasing and confirm they want to proceed.
- Call the purchase tool AT MOST ONCE per user request. After a successful purchase, \
STOP calling tools and report the results (data received and credits spent) to the user.
- If the purchase returns an error or empty results, report the problem — do NOT retry.
- If budget limits are exceeded, explain the situation and suggest alternatives.
- You can purchase from different sellers by providing their URL."""

_A2A_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the A2A (Agent-to-Agent) protocol with Nevermined payments.

Sellers can come from (1) local registration when they start with --buyer-url, \
(2) discover_economy_sellers from the hackathon Discovery API, or (3) discover_agent by URL.

Your workflow (do each step once, in order):
1. **discover_economy_sellers** — Fetch sellers from the hackathon economy (optional category). \
All economy sellers are returned; those with plan IDs and a callable URL are registered for list_sellers and purchase_a2a.
2. **list_sellers** — See all registered sellers (local + economy) and their capabilities.
3. **discover_agent** — (Optional) Manually discover a seller by URL if needed.
4. **search_marketplace** — (Optional) When the user wants to find agents by description, use RateGenius: \
e.g. \"find agents for social media sentiment\" or \"search marketplace for blockchain analytics\". Costs 3 credits per search.
5. **check_balance** — Check your credit balance and budget.
6. **purchase_a2a** — Send an A2A message with automatic payment (FINAL STEP).

After purchase_a2a completes, you are DONE. Report the results and stop.
""" + _GUIDELINES

_AGENTCORE_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the A2A (Agent-to-Agent) protocol with Nevermined payments.

Use discover_economy_sellers to fetch sellers from the hackathon economy, then \
list_sellers to see them. Do NOT try to discover sellers by URL — agent card \
discovery is not available in this environment.

Your workflow (do each step once, in order):
1. **discover_economy_sellers** — Fetch sellers from the hackathon economy (optional category).
2. **list_sellers** — See all registered sellers and their capabilities.
3. **search_marketplace** — (Optional) Find agents by description (RateGenius, 3 credits per search).
4. **check_balance** — Check your credit balance and budget.
5. **purchase_a2a** — Send an A2A message with automatic payment (FINAL STEP).

After purchase_a2a completes, you are DONE. Report the results and stop.

Important guidelines:
- Use list_sellers to see what sellers are available and their costs.
- Always check the balance before making a purchase.
- Tell the user the expected cost BEFORE purchasing and confirm they want to proceed.
- Call purchase_a2a AT MOST ONCE per user request. After it returns, STOP calling \
tools and report the results (data received and credits spent) to the user.
- If purchase_a2a returns an error or empty results, report the problem — do NOT retry.
- If budget limits are exceeded, explain the situation and suggest alternatives.
- Go directly to purchase_a2a after confirming with the user — do not try to fetch agent cards."""

_HTTP_PROMPT = """\
You are a data buying agent. You help users discover and purchase data from \
sellers using the x402 HTTP payment protocol.

Your workflow (do each step once, in order):
1. **discover_pricing** — Call this first to see what the seller offers.
2. **check_balance** — Check your credit balance and budget before purchasing.
3. **purchase_data** — Buy data by sending an x402-protected HTTP request (FINAL STEP).

After step 3 completes, you are DONE. Report the results and stop.
""" + _GUIDELINES

_A2A_TOOLS = [discover_economy_sellers, list_sellers, discover_agent, check_balance, search_marketplace, purchase_a2a]
_AGENTCORE_TOOLS = [discover_economy_sellers, list_sellers, check_balance, search_marketplace, purchase_a2a]
_HTTP_TOOLS = [discover_pricing, check_balance, purchase_data]


def create_agent(model, mode: str = "a2a") -> Agent:
    """Create a Strands agent with the given model.

    Args:
        model: A Strands-compatible model (OpenAIModel, BedrockModel, etc.)
        mode: Agent mode — "a2a" for A2A marketplace tools (default),
              "http" for direct x402 HTTP tools,
              "agentcore" for AgentCore deployment (no discover_agent).

    Returns:
        Configured Strands Agent with buyer tools.
    """
    if mode == "a2a":
        tools = _A2A_TOOLS
        prompt = _A2A_PROMPT
    elif mode == "agentcore":
        tools = _AGENTCORE_TOOLS
        prompt = _AGENTCORE_PROMPT
    elif mode == "http":
        tools = _HTTP_TOOLS
        prompt = _HTTP_PROMPT
    else:
        raise ValueError(f"Invalid mode {mode!r}, must be 'a2a', 'agentcore', or 'http'")
    return Agent(
        model=model,
        tools=tools,
        system_prompt=prompt,
    )
