"""Purchase from RateGenius — x402 + POST /service (marketplace price discovery).

RateGenius is not standard A2A; it exposes POST /service with a custom body.
This module gets an x402 token and POSTs to /service with payment-signature.
"""

import json
import os
import time

import httpx

from payments_py import Payments

from ..log import get_logger, log
from .token_options import build_token_options

_logger = get_logger("buyer.rategenius")

# Defaults from RateGenius integration guide; override via env
RATEGENIUS_URL = os.getenv(
    "RATEGENIUS_URL",
    "https://unsyllabified-wearifully-blaise.ngrok-free.dev",
).rstrip("/")
RATEGENIUS_PLAN_ID = os.getenv(
    "RATEGENIUS_PLAN_ID",
    "97866696145535066453103713195260098266633201693062554670376824816568438944699",
)
RATEGENIUS_AGENT_ID = os.getenv(
    "RATEGENIUS_AGENT_ID",
    "19382499784507691897099813046158899650802606062565712631387582302174094534652",
)


def _error(message: str) -> dict:
    return {"status": "error", "content": [{"text": message}], "credits_used": 0}


def purchase_rategenius_impl(
    payments: Payments,
    query: str,
    budget_max: float | None = None,
    top_k: int = 5,
    agent_url: str | None = None,
    plan_id: str | None = None,
    agent_id: str | None = None,
) -> dict:
    """Call RateGenius POST /service with x402 payment.

    Args:
        payments: Initialized Payments SDK.
        query: Plain-English description of the service you need.
        budget_max: Optional max price per request in USD.
        top_k: Max number of results (default 5).
        agent_url: RateGenius base URL (default from env).
        plan_id: RateGenius plan ID (default from env).
        agent_id: RateGenius agent ID (default from env).

    Returns:
        dict with status, content (for Strands), response summary, credits_used.
    """
    base = (agent_url or RATEGENIUS_URL).rstrip("/")
    pid = plan_id or RATEGENIUS_PLAN_ID
    aid = agent_id or RATEGENIUS_AGENT_ID

    log(_logger, "RATEGENIUS", "CONNECT", f"url={base} plan={pid[:12]}")

    try:
        token_options = build_token_options(payments, pid)
        token_result = payments.x402.get_x402_access_token(
            plan_id=pid,
            agent_id=aid,
            token_options=token_options,
        )
        access_token = token_result.get("accessToken")
        if not access_token:
            return _error(
                "Failed to generate x402 token for RateGenius. "
                "Buy credits on RateGenius's plan at nevermined.app (plan 97866696...)."
            )

        body = {"query": query, "top_k": top_k}
        if budget_max is not None:
            body["budget_max"] = budget_max

        headers = {
            "Content-Type": "application/json",
            "payment-signature": access_token,
        }
        # ngrok free tier returns 404/interstitial unless we skip the browser warning
        if "ngrok" in base.lower():
            headers["ngrok-skip-browser-warning"] = "1"

        log(_logger, "RATEGENIUS", "SEND", f'query="{query[:50]}"')
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{base}/service", headers=headers, json=body)

        # #region agent log
        if resp.status_code != 200:
            try:
                _lp = "/Users/laughingbull/Sandbox/dev/apps/hackathons/.cursor/debug-542f5b.log"
                _payload = {
                    "sessionId": "542f5b",
                    "location": "purchase_rategenius.py",
                    "message": "RateGenius response",
                    "data": {"status": resp.status_code, "body_preview": (resp.text or "")[:200]},
                    "timestamp": int(time.time() * 1000),
                    "hypothesisId": "ngrok",
                }
                with open(_lp, "a") as _f:
                    _f.write(json.dumps(_payload) + "\n")
            except Exception:
                pass
        # #endregion

        if resp.status_code == 402:
            return _error(
                "RateGenius returned 402 Payment Required. "
                "Purchase credits on their plan at nevermined.app."
            )
        if resp.status_code == 400:
            return _error("RateGenius: missing or invalid query.")
        if resp.status_code != 200:
            return _error(f"RateGenius returned HTTP {resp.status_code}.")

        data = resp.json()
        credits_charged = data.get("credits_charged", 3)
        total_found = data.get("total_found", 0)
        results = data.get("results", [])
        recommendation = data.get("recommendation", "")
        best = data.get("best_agent", {})

        lines = [
            f"RateGenius search: '{query}'",
            f"Credits charged: {credits_charged}",
            f"Agents found: {total_found}",
        ]
        if recommendation:
            lines.append(f"Recommendation: {recommendation}")
        if best:
            lines.append(
                f"Best match: {best.get('name', '')} — {best.get('endpoint_url', '')} "
                f"({best.get('price_raw', '')})"
            )
        for i, r in enumerate(results[:5], 1):
            lines.append(
                f"  {i}. {r.get('name', '')} — {r.get('price_raw', '')} "
                f"(relevance: {r.get('relevance_score', 0):.0%})"
            )

        text = "\n".join(lines)
        log(_logger, "RATEGENIUS", "DONE", f"credits={credits_charged} found={total_found}")

        return {
            "status": "success",
            "content": [{"text": text}],
            "response": text,
            "credits_used": credits_charged,
            "rategenius": data,
        }
    except (ConnectionError, OSError) as e:
        log(_logger, "RATEGENIUS", "ERROR", f"connect: {e}")
        return _error(f"Cannot connect to RateGenius at {base}. Is the URL correct?")
    except Exception as e:
        log(_logger, "RATEGENIUS", "ERROR", str(e))
        return _error(f"RateGenius request failed: {e}")
