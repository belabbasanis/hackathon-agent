#!/usr/bin/env python3
"""Try to buy from every discovered agent until one succeeds.

Usage:
    cd agents/buyer-simple-agent
    poetry run python buy_from_any.py [--query "your query"]

Requires .env with NVM_API_KEY (subscriber key). Discovers sellers from the
hackathon economy, then attempts purchase from each until one succeeds.
"""

import argparse
import os
import sys

# Ensure src is importable when run from buyer-simple-agent root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from payments_py import Payments, PaymentOptions

from src.tools.discover_economy import discover_economy_impl
from src.tools.discover_a2a import discover_agent_impl
from src.tools.purchase_a2a import purchase_a2a_impl


def _callable_url(endpoint_url: str) -> str | None:
    if not endpoint_url or not str(endpoint_url).strip().startswith(("http://", "https://")):
        return None
    return str(endpoint_url).strip().rstrip("/")


def _get_plan_and_agent_id(seller: dict) -> tuple[str, str]:
    """Extract plan_id and agent_id from discovery seller or agent card."""
    plan_ids = seller.get("planIds") or []
    plan_pricing = seller.get("planPricing") or []
    if plan_ids:
        plan_id = plan_ids[0]
    elif plan_pricing and isinstance(plan_pricing[0], dict):
        plan_id = plan_pricing[0].get("planDid", "")
    else:
        plan_id = ""
    agent_id = seller.get("nvmAgentId", "")

    if plan_id and not agent_id:
        url = _callable_url(seller.get("endpointUrl", ""))
        if url:
            try:
                result = discover_agent_impl(url)
                if result.get("status") == "success" and result.get("payment"):
                    agent_id = result["payment"].get("agentId", "")
            except Exception:
                pass
    return plan_id, agent_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Buy from any agent until one succeeds")
    parser.add_argument(
        "--query",
        default="search for bitcoin price",
        help="Query to send to agents (default: search for bitcoin price)",
    )
    parser.add_argument(
        "--category",
        default="",
        help="Optional category filter for discovery",
    )
    args = parser.parse_args()

    nvm_key = os.environ.get("NVM_API_KEY", "").strip()
    if not nvm_key or "your-" in nvm_key.lower():
        print("ERROR: Set NVM_API_KEY in .env (subscriber key from nevermined.app)")
        sys.exit(1)

    env = os.environ.get("NVM_ENVIRONMENT", "sandbox")
    payments = Payments.get_instance(
        PaymentOptions(nvm_api_key=nvm_key, environment=env)
    )

    print("Discovering sellers from hackathon economy...")
    result = discover_economy_impl(
        nvm_key,
        side="sell",
        category=args.category.strip() or None,
    )
    sellers = result.get("sellers", [])
    if result.get("status") != "success" or not sellers:
        print("No sellers found. Check NVM_API_KEY and try again.")
        sys.exit(1)

    candidates = []
    for s in sellers:
        url = _callable_url(s.get("endpointUrl", ""))
        if not url:
            continue
        plan_id, agent_id = _get_plan_and_agent_id(s)
        if not plan_id:
            continue
        candidates.append({
            "name": s.get("name", "Unknown"),
            "url": url,
            "plan_id": plan_id,
            "agent_id": agent_id,
        })

    if not candidates:
        print("No sellers with plan ID and callable URL found.")
        sys.exit(1)

    print(f"Found {len(candidates)} purchase-ready sellers. Trying each until one succeeds...\n")

    for i, c in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] {c['name']} ({c['url']})")
        try:
            out = purchase_a2a_impl(
                payments=payments,
                plan_id=c["plan_id"],
                agent_url=c["url"],
                agent_id=c["agent_id"],
                query=args.query,
            )
            if out.get("status") == "success":
                print("\n" + "=" * 60)
                print("SUCCESS!")
                print("=" * 60)
                print(f"Agent: {c['name']}")
                print(f"Credits used: {out.get('credits_used', 0)}")
                print("\nResponse:")
                text = out.get("response") or (out.get("content", [{}])[0].get("text", ""))
                print(text[:2000] + ("..." if len(text) > 2000 else ""))
                return
            err = (out.get("content") or [{}])[0].get("text", "Unknown error")
            print(f"  Failed: {err[:120]}")
        except Exception as e:
            print(f"  Error: {e}")
        print()

    print("No agent succeeded. All attempts failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()
