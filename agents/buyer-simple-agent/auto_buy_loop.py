#!/usr/bin/env python3
"""Automate buying attempts: run discovery + purchase in a loop until success.

Runs buy_from_any logic repeatedly, skipping unreachable URLs, with configurable
interval and max runs. Logs all attempts to a file.

Usage:
    cd agents/buyer-simple-agent
    poetry run python auto_buy_loop.py
    poetry run python auto_buy_loop.py --interval 60 --max-runs 10
    poetry run python auto_buy_loop.py --daemon --log-file auto_buy.log

Requires .env with NVM_API_KEY (subscriber key).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

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


def _skip_url(url: str) -> bool:
    """Skip URLs that are likely unreachable from this machine."""
    if not url:
        return True
    lower = url.lower()
    skip_hosts = (
        "localhost",
        "127.0.0.1",
        "disabled.example.com",
        "seller:",
        ".loca.lt",
        ".trycloudflare.com",
    )
    return any(h in lower for h in skip_hosts)


def _get_plan_and_agent_id(seller: dict) -> tuple[str, str]:
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


def run_one_attempt(
    payments,
    nvm_key: str,
    query: str,
    category: str | None,
    skip_unreachable: bool,
    log_fn=None,
) -> tuple[bool, str | None]:
    """Run one full discovery + purchase attempt. Returns (success, winner_name)."""
    result = discover_economy_impl(nvm_key, side="sell", category=category)
    sellers = result.get("sellers", [])
    if result.get("status") != "success" or not sellers:
        return False, None

    candidates = []
    for s in sellers:
        url = _callable_url(s.get("endpointUrl", ""))
        if not url:
            continue
        if skip_unreachable and _skip_url(url):
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

    if log_fn:
        log_fn(f"Trying {len(candidates)} agents...")

    for i, c in enumerate(candidates, 1):
        if log_fn:
            log_fn(f"  [{i}/{len(candidates)}] {c['name']}")
        try:
            out = purchase_a2a_impl(
                payments=payments,
                plan_id=c["plan_id"],
                agent_url=c["url"],
                agent_id=c["agent_id"],
                query=query,
            )
            if out.get("status") == "success":
                return True, c["name"]
        except Exception:
            pass
    return False, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Automate buying attempts in a loop")
    parser.add_argument("--query", default="search for bitcoin price", help="Query to send")
    parser.add_argument("--category", default="", help="Category filter")
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Seconds between full discovery+attempt cycles (default: 120)",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="Max discovery cycles (0 = unlimited)",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Do NOT skip localhost/disabled URLs (try all)",
    )
    parser.add_argument(
        "--log-file",
        default="auto_buy.log",
        help="Log file path (default: auto_buy.log)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously until success or Ctrl+C",
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

    skip_unreachable = not args.no_skip
    category = args.category.strip() or None
    run_id = 0

    def log(msg: str, also_print: bool = True) -> None:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}] {msg}"
        if also_print:
            print(line)
        try:
            with open(args.log_file, "a") as f:
                f.write(line + "\n")
        except Exception:
            pass

    log("auto_buy_loop started")
    log(f"  query={args.query!r} interval={args.interval}s skip_unreachable={skip_unreachable}")

    while True:
        run_id += 1
        if args.max_runs and run_id > args.max_runs:
            log(f"Reached max runs ({args.max_runs}). Stopping.")
            sys.exit(1)

        log(f"--- Run {run_id} ---")
        try:
            success, winner = run_one_attempt(
                payments, nvm_key, args.query, category, skip_unreachable, log_fn=log
            )
            if success:
                log(f"SUCCESS! Purchased from: {winner}")
                sys.exit(0)
            log("No agent succeeded this run.")
        except Exception as e:
            log(f"Run error: {e}")

        if not args.daemon:
            log("Single run complete. Use --daemon to loop.")
            sys.exit(1)

        log(f"Sleeping {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
