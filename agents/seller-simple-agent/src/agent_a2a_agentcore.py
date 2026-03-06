"""
AgentCore-aware A2A server entry point for the data selling agent.

Wraps the standard A2A server (agent_a2a.py) with AgentCore compatibility:
- Reads port from $PORT env var (set by AgentCore runtime)
- Sets agent card URL from $AGENT_URL env var (AgentCore public URL)
- Adds header remapping middleware so `payment-signature` survives the proxy
- Includes /ping health check endpoint

AgentCore's proxy strips custom HTTP headers. Only headers prefixed with
`X-Amzn-Bedrock-AgentCore-Runtime-Custom-` pass through. The middleware
below copies the prefixed header to `payment-signature` before the
PaymentsA2AServer middleware sees it.

Usage:
    poetry run agent-a2a-agentcore
    PORT=8080 AGENT_URL=https://my-agent.agentcore.aws python -m src.agent_a2a_agentcore
"""

import asyncio
import base64
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.types import ASGIApp, Receive, Scope, Send
from strands.models.openai import OpenAIModel

from payments_py import Payments, PaymentOptions
from payments_py.a2a.agent_card import build_payment_agent_card
from payments_py.a2a.server import PaymentsA2AServer
from payments_py.x402.helpers import build_payment_required

from .agent_a2a import StrandsA2AExecutor
from .log import get_logger, log
from .strands_agent_plain import create_plain_agent, resolve_tools

load_dotenv()

# Fail fast with a clear message if required env vars are missing (e.g. on Railway)
_missing = []
if not os.environ.get("NVM_API_KEY"):
    _missing.append("NVM_API_KEY")
if not os.environ.get("NVM_PLAN_ID"):
    _missing.append("NVM_PLAN_ID")
if _missing:
    print("ERROR: Missing required environment variables. Set them in Railway → Variables (or .env locally):")
    for k in _missing:
        print(f"  - {k}")
    sys.exit(1)

NVM_API_KEY = os.environ["NVM_API_KEY"]
NVM_ENVIRONMENT = os.getenv("NVM_ENVIRONMENT", "sandbox")
NVM_PLAN_ID = os.environ["NVM_PLAN_ID"]
NVM_AGENT_ID = os.environ.get("NVM_AGENT_ID", "")

# AgentCore / Railway: use PORT env (default 8080). Railway "Generate Domain" must target 8080.
PORT = int(os.getenv("PORT", "8080"))


def _resolve_agent_url() -> str:
    """Public URL for the agent card. Prefer AGENT_URL; on Railway use RAILWAY_PUBLIC_DOMAIN if set."""
    if u := os.getenv("AGENT_URL", "").strip():
        return u
    if d := os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip():
        return f"https://{d}"
    return f"http://localhost:{PORT}"


AGENT_URL = _resolve_agent_url()

_logger = get_logger("seller.agentcore")

AGENTCORE_HEADER = b"x-amzn-bedrock-agentcore-runtime-custom-payment-signature"

if not NVM_AGENT_ID:
    log(_logger, "SERVER", "ERROR",
        "NVM_AGENT_ID is required for A2A mode. "
        "Set it in your .env file (find it in the Nevermined App agent settings).")
    sys.exit(1)

payments = Payments.get_instance(
    PaymentOptions(nvm_api_key=NVM_API_KEY, environment=NVM_ENVIRONMENT)
)


# ---------------------------------------------------------------------------
# Endpoint validation probe (Nevermined Protected URL validation)
# ---------------------------------------------------------------------------

# Nevermined's validator POSTs to the endpoint without a payment token and
# expects 200. Return 200 for POST / with no payment-signature so validation
# passes; real clients send payment-signature and get the normal A2A flow.
_VALIDATION_RESPONSE = (
    b'{"jsonrpc":"2.0","id":null,"result":{"status":"ok",'
    b'"message":"Endpoint protected. Send payment-signature header for A2A requests."}}'
)


def _is_root_post(path: str) -> bool:
    """True if path is the A2A root (/) or AgentCore invocation path (/invocations)."""
    p = (path or "").strip()
    return p == "" or p == "/" or p == "/invocations"


class EndpointValidationMiddleware:
    """ASGI middleware: pass through to app. Nevermined shows green for Protected Endpoint when they get 402 (payment required), not 200."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # No shortcut: let POST / and POST /invocations without token reach the payment layer,
        # which returns 402. Nevermined validator expects 402 for "Protected Endpoint" to show green.
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Header remapping middleware
# ---------------------------------------------------------------------------

class AgentCoreHeaderMiddleware:
    """ASGI middleware that remaps AgentCore custom headers to payment-signature.

    AgentCore strips all custom headers except those prefixed with
    X-Amzn-Bedrock-AgentCore-Runtime-Custom-. This middleware copies
    the prefixed payment header into the standard `payment-signature`
    header so downstream middleware (PaymentsA2AServer) can read it.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            # AgentCore routes all traffic to /invocations; rewrite to /
            # so the A2A JSON-RPC handler (registered at POST /) receives it.
            if scope.get("path") == "/invocations":
                scope["path"] = "/"
                scope["raw_path"] = b"/"

            headers = list(scope.get("headers", []))
            has_payment_sig = any(k == b"payment-signature" for k, _ in headers)

            if not has_payment_sig:
                for key, value in headers:
                    if key == AGENTCORE_HEADER:
                        headers.append((b"payment-signature", value))
                        log(_logger, "MIDDLEWARE", "REMAP",
                            "copied AgentCore custom header -> payment-signature")
                        break
                scope["headers"] = headers

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Start the A2A server with AgentCore compatibility."""
    # Resolve tools (default: all)
    tools_list, credit_map, skills = resolve_tools(None)

    cost_parts = [f"{name}={cost}" for name, cost in credit_map.items()]
    cost_description = "Credits vary by tool: " + ", ".join(cost_parts)

    # Build agent card with the AgentCore public URL
    base_agent_card = {
        "name": "Data Selling Agent",
        "description": (
            "AI-powered data agent that provides web search, content summarization, "
            "and market research services with tiered pricing."
        ),
        "url": AGENT_URL,
        "version": "0.1.0",
        "skills": [s.model_dump() for s in skills],
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
        },
    }

    agent_card = build_payment_agent_card(
        base_agent_card,
        {
            "paymentType": "dynamic",
            "credits": min(credit_map.values()),
            "planId": NVM_PLAN_ID,
            "agentId": NVM_AGENT_ID,
            "costDescription": cost_description,
        },
    )

    # Create strands agent and executor
    model = OpenAIModel(
        client_args={"api_key": os.environ.get("OPENAI_API_KEY", "")},
        model_id=os.getenv("MODEL_ID", "gpt-4o-mini"),
    )

    agent = create_plain_agent(model, None)
    executor = StrandsA2AExecutor(agent, credit_map)

    log(_logger, "SERVER", "STARTUP",
        f"Data Selling Agent — AgentCore A2A on port {PORT}")
    log(_logger, "SERVER", "STARTUP", f"agent_url={AGENT_URL}")
    log(_logger, "SERVER", "STARTUP",
        f"plan={NVM_PLAN_ID} agent={NVM_AGENT_ID} env={NVM_ENVIRONMENT}")
    log(_logger, "SERVER", "STARTUP", f"pricing={cost_description}")

    # Payment lifecycle hooks for logging
    async def _before_request(method, params, request):
        token = request.headers.get("payment-signature", "")
        token_preview = f"{token[:16]}..." if len(token) > 16 else token or "(none)"
        log(_logger, "PAYMENT", "VERIFY", f"method={method} token={token_preview}")

    async def _after_request(method, response, request):
        status = getattr(response, "status_code", "ok")
        log(_logger, "PAYMENT", "VERIFIED", f"method={method} status={status}")

    async def _on_error(method, exc, request):
        log(_logger, "PAYMENT", "ERROR", f"method={method} error={exc}")

    hooks = {
        "beforeRequest": _before_request,
        "afterRequest": _after_request,
        "onError": _on_error,
    }

    # Create FastAPI app with health check
    fastapi_app = FastAPI(title="Data Selling Agent (AgentCore)")

    @fastapi_app.get("/ping")
    async def ping():
        return {"status": "ok"}

    @fastapi_app.get("/")
    async def root():
        """Return 200 for GET / so Nevermined Protected Endpoint validation (GET) can show green."""
        return {"status": "ok", "message": "Data Selling Agent A2A; use POST / with payment-signature for requests."}

    @fastapi_app.post("/validate")
    async def validate_endpoint():
        """Return 200 for Nevermined Protected Endpoint URL validation. No payment required."""
        return {"status": "ok", "message": "Endpoint reachable"}

    # Serve agent card with URL from the request so it's correct behind proxies (Railway, etc.)
    # even when AGENT_URL env is not set. Registered before PaymentsA2AServer so this route wins.
    @fastapi_app.get("/.well-known/agent.json")
    async def well_known_agent(request: Request):
        # Use X-Forwarded-Proto/Host so the card URL is https when behind Railway or other TLS proxies
        proto = request.headers.get("x-forwarded-proto", "").strip().lower() or request.url.scheme
        host = request.headers.get("x-forwarded-host", "").strip() or request.url.netloc
        base_url = f"{proto}://{host}".rstrip("/")
        card = agent_card.model_dump() if hasattr(agent_card, "model_dump") else dict(agent_card)
        card["url"] = base_url
        return card

    # Nevermined query-agents style: POST /prompt with {"query": "..."} and payment-signature header
    # https://nevermined.ai/docs/development-guide/query-agents
    max_credits = max(credit_map.values()) if credit_map else 10

    class PromptBody(BaseModel):
        query: str
        parameters: dict | None = None

    @fastapi_app.post("/prompt")
    async def prompt(request: Request, body: PromptBody):
        """Simple query endpoint per Nevermined docs: verify → execute → settle."""
        payment_required = build_payment_required(
            plan_id=NVM_PLAN_ID,
            endpoint=str(request.url),
            agent_id=NVM_AGENT_ID,
            http_verb="POST",
        )
        token = request.headers.get("payment-signature")
        if not token:
            encoded = base64.b64encode(
                payment_required.model_dump_json(by_alias=True).encode()
            ).decode()
            return JSONResponse(
                status_code=402,
                content={"error": "Payment Required", "message": "Send x402 token in payment-signature header"},
                headers={"payment-required": encoded},
            )
        try:
            verification = payments.facilitator.verify_permissions(
                payment_required=payment_required,
                x402_access_token=token,
                max_amount=str(max_credits),
            )
        except Exception as e:
            log(_logger, "PAYMENT", "PROMPT_VERIFY_FAIL", str(e))
            return JSONResponse(status_code=402, content={"error": f"Token verification failed: {e}"})
        if not verification.is_valid:
            return JSONResponse(
                status_code=402,
                content={"error": getattr(verification, "invalid_reason", "Invalid token")},
            )
        try:
            result = await asyncio.to_thread(agent, body.query)
            response_text = str(result)
        except Exception as e:
            log(_logger, "PAYMENT", "PROMPT_EXEC_FAIL", str(e))
            return JSONResponse(status_code=500, content={"error": str(e)})
        payments.facilitator.settle_permissions(
            payment_required=payment_required,
            x402_access_token=token,
            max_amount=str(max_credits),
        )
        return {"response": response_text}

    # Pass our app to PaymentsA2AServer so it adds A2A + payment routes to it
    result = PaymentsA2AServer.start(
        agent_card=agent_card,
        executor=executor,
        payments_service=payments,
        port=PORT,
        hooks=hooks,
        app=fastapi_app,
    )

    # Add header remapping middleware AFTER PaymentsA2AServer.start() so it
    # wraps the payment middleware. Starlette executes middleware in reverse
    # order of addition, so this middleware runs FIRST — remapping the
    # AgentCore custom header to payment-signature before the payment
    # middleware checks for it.
    fastapi_app.add_middleware(AgentCoreHeaderMiddleware)
    # Pass through so POST / without token returns 402 (Nevermined shows green for Protected Endpoint when they get 402).
    fastapi_app.add_middleware(EndpointValidationMiddleware)
    # CORS so browsers and Nevermined frontend can GET agent.json and OPTIONS preflight succeeds
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    log(_logger, "SERVER", "STARTUP", "AgentCore header remapping + endpoint validation + CORS middleware active")

    # Use uvicorn.run() directly so we can bind to 0.0.0.0 (required in containers)
    import uvicorn

    uvicorn.run(fastapi_app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    main()
