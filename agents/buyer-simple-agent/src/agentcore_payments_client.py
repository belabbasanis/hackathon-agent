"""AgentCore-compatible PaymentsClient with SigV4 signing.

AgentCore's proxy:
1. Strips all custom HTTP headers except those prefixed with
   X-Amzn-Bedrock-AgentCore-Runtime-Custom-
2. Requires SigV4-signed requests to reach deployed agent runtimes

This subclass adds:
- Dual headers (standard + AgentCore-prefixed) so x402 tokens survive the proxy
- SigV4 signing on outgoing requests so the buyer can invoke AgentCore-hosted sellers
- URL handling for AgentCore invoke endpoints (no trailing-slash mangling)
"""

import json
import os
from urllib.parse import quote
from uuid import uuid4

import httpx
from boto3 import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from payments_py.a2a.payments_client import PaymentsClient

from .log import get_logger, log

_logger = get_logger("buyer.sigv4")

AGENTCORE_HEADER = "x-amzn-bedrock-agentcore-runtime-custom-payment-signature"
AGENTCORE_HOST_PREFIX = "bedrock-agentcore"


def is_agentcore_url(url: str) -> bool:
    """Check if a URL points to an AgentCore endpoint."""
    return AGENTCORE_HOST_PREFIX in url


def build_agentcore_url(agent_arn: str, region: str = "us-west-2") -> str:
    """Build the AgentCore InvokeAgentRuntime URL from an agent runtime ARN.

    Usage:
        url = build_agentcore_url("arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-agent")
        # -> https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/<encoded>/invocations?qualifier=DEFAULT
    """
    encoded_arn = quote(agent_arn, safe="")
    return (
        f"https://bedrock-agentcore.{region}.amazonaws.com"
        f"/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    )


def _extract_arn_from_url(url: str) -> str:
    """Extract the agent runtime ARN from an AgentCore invocations URL."""
    # URL format: .../runtimes/{encoded_arn}/invocations?qualifier=DEFAULT
    from urllib.parse import unquote
    parts = url.split("/runtimes/")
    if len(parts) < 2:
        return ""
    arn_part = parts[1].split("/invocations")[0]
    return unquote(arn_part)


class SigV4HttpxAuth(httpx.Auth):
    """httpx Auth class that applies AWS SigV4 signing to every request.

    Uses the default credential chain (works inside AgentCore containers
    via ECS task role / container credentials).
    """

    def __init__(
        self,
        service: str = "bedrock-agentcore",
        region: str | None = None,
    ):
        self.service = service
        self.region = region or os.environ.get("AWS_REGION", "us-west-2")
        self._session = Session()

    def auth_flow(self, request: httpx.Request):
        credentials = self._session.get_credentials().get_frozen_credentials()

        # Only include headers that should be signed.  httpx adds headers
        # like accept-encoding, connection, user-agent that it may later
        # modify — signing them causes a SigV4 signature mismatch.
        sign_headers = {"host": request.headers["host"]}
        if "content-type" in request.headers:
            sign_headers["content-type"] = request.headers["content-type"]
        # Include x-amzn-* headers (AgentCore custom payment header, etc.)
        for key in request.headers:
            if key.startswith("x-amzn-"):
                sign_headers[key] = request.headers[key]

        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=sign_headers,
        )
        SigV4Auth(credentials, self.service, self.region).add_auth(aws_request)

        # Copy SigV4 headers (Authorization, X-Amz-Date, X-Amz-Security-Token)
        for key, value in aws_request.headers.items():
            request.headers[key] = value

        log(_logger, "SIGV4", "SIGNED",
            f"method={request.method} url={str(request.url)[:80]}")

        yield request


async def _log_error_response(response: httpx.Response):
    """Log error response bodies for debugging."""
    if response.status_code >= 400:
        await response.aread()
        body = response.text[:500]
        log(_logger, "HTTP", "ERROR",
            f"status={response.status_code} url={str(response.url)[:80]} body={body}")


class AgentCorePaymentsClient(PaymentsClient):
    """PaymentsClient with SigV4 signing and AgentCore-safe headers.

    When the seller URL is an AgentCore endpoint (contains 'bedrock-agentcore'),
    requests are automatically SigV4-signed using the container's IAM role.
    The x402 payment token is sent via both the standard header and the
    AgentCore-prefixed header.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # PaymentsClient appends "/" to the URL, which mangles AgentCore query
        # strings (qualifier=DEFAULT becomes qualifier=DEFAULT/).  Strip it.
        if is_agentcore_url(self._agent_base_url):
            self._agent_base_url = self._agent_base_url.rstrip("/")
            log(_logger, "CLIENT", "INIT",
                f"AgentCore URL (SigV4 enabled): {self._agent_base_url[:80]}")

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "payment-signature": token,
            AGENTCORE_HEADER: token,
        }

    def _get_client(self):
        """Create A2A client with SigV4-signed httpx transport for AgentCore."""
        if self._client is None:
            from a2a.client.client import ClientConfig
            from a2a.client.client_factory import ClientFactory, minimal_agent_card

            client_kwargs: dict = {
                "timeout": httpx.Timeout(60.0),
                "event_hooks": {"response": [_log_error_response]},
            }

            if is_agentcore_url(self._agent_base_url):
                client_kwargs["auth"] = SigV4HttpxAuth()
                log(_logger, "CLIENT", "SIGV4", "SigV4 auth enabled for httpx client")

            http_client = httpx.AsyncClient(**client_kwargs)
            factory = ClientFactory(
                config=ClientConfig(streaming=True, httpx_client=http_client)
            )
            client = factory.create(minimal_agent_card(self._agent_base_url))

            try:
                if hasattr(client, "_card") and hasattr(client._card, "capabilities"):
                    setattr(client._card.capabilities, "streaming", True)
                if hasattr(client._card, "supports_authenticated_extended_card"):
                    setattr(
                        client._card, "supports_authenticated_extended_card", False
                    )
            except Exception:
                pass

            self._client = client
        return self._client
