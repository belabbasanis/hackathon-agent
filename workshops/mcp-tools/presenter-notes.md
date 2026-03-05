# Workshop: Nevermined x MCP — Monetizing AI Tools

**Duration:** 45-60 minutes
**Goal:** Participants build a monetized MCP server with paid tools, resources, and prompts using PaymentsMCP (Python) and the imperative API (TypeScript), then test it with a JSON-RPC client.

---

## Format Recommendation

| Element | Recommendation |
|---------|----------------|
| **Slides** | Use the Keynote in this folder (`MCP Tools.key`) |
| **Live demo** | Primary format — build the server step by step |
| **Terminal** | Two terminals: MCP server + client |
| **Browser** | Optional — show Claude Code or Cursor connecting to the server |

**Why step-by-step build:** MCP has three primitives (tools, resources, prompts) plus dynamic pricing and observability. Building one at a time lets participants absorb each concept.

---

## Pre-Workshop Checklist

### Your machine (presenter)

- [ ] `payments-py` installed (`pip install payments-py`)
- [ ] `@nevermined-io/payments` installed (>= 1.1.5)
- [ ] Valid `NVM_API_KEY` (sandbox builder key)
- [ ] `NVM_AGENT_ID` and `NVM_PLAN_ID` set
- [ ] A second API key (`NVM_SUBSCRIBER_API_KEY`) for subscriber/client testing
- [ ] Workshop files tested: `python server.py` starts, `python client.py` calls tools
- [ ] Port 3000 free for the MCP server
- [ ] (Optional) Claude Code or Cursor installed for the "connecting AI assistants" demo

### Participant machines

- [ ] Python 3.10+ or Node.js 18+
- [ ] Nevermined sandbox account + API key

---

## Agenda

| Time | Section | Format | Files |
|------|---------|--------|-------|
| 0:00 - 0:05 | What is MCP + why monetize tools? | Slides | — |
| 0:05 - 0:20 | Building the MCP server (Python) | Live code | `server.py` |
| 0:20 - 0:30 | Building the MCP server (TypeScript) | Live code | `server.ts` |
| 0:30 - 0:40 | Testing with the client | Live code | `client.py` / `client.ts` |
| 0:40 - 0:50 | Dynamic pricing + observability | Discussion + code | — |
| 0:50 - 1:00 | Q&A | Open | — |

---

## Detailed Script

### Section 1: What is MCP (5 min)

**Key talking points:**

> "MCP — Model Context Protocol — is how AI assistants like Claude Code and Cursor discover and call external tools. It's becoming THE distribution channel for AI tools. Build a tool, expose it via MCP, and every AI assistant that supports the protocol can use it."

> "With Nevermined, you can charge per tool call. The x402 token is sent as a Bearer token. Same verify-and-settle flow as HTTP, but wrapped in the MCP protocol with OAuth 2.1."

---

### Section 2: Python MCP Server (15 min)

**Open `python/server.py`**

> "In Python, we use the `PaymentsMCP` class from `payments_py.mcp`. One class handles everything."

#### Step 1: Initialize

```python
import urllib3
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions
from payments_py.mcp import PaymentsMCP

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.getenv("NVM_API_KEY", ""),
        environment=os.getenv("NVM_ENVIRONMENT", "sandbox"),
    )
)

mcp = PaymentsMCP(
    payments,
    name="my-mcp-server",
    agent_id=os.getenv("NVM_AGENT_ID", ""),
    version="1.0.0",
    description="Paid search and analysis tools",
)
```

> "Two boilerplate lines at the top: `load_dotenv()` loads your `.env` file, and `urllib3.disable_warnings()` silences SSL warnings in sandbox. Then `Payments.get_instance()` — note it's a class method, not a constructor — gives you the SDK instance."

> "The server name is important — it becomes part of the logical URI: `mcp://my-mcp-server/tools/search`. Same registration works on localhost or production."

#### Step 2: Add a tool (fixed credits)

```python
@mcp.tool(name="search", description="Search the web for information", credits=1)
async def search(query: str) -> str:
    return f"Results for: {query}"
```

> "The decorator extracts the input schema from type hints — no manual JSON schema. It validates the x402 token before execution and burns credits after."

#### Step 3: Add a tool (dynamic credits)

```python
def price_by_length(context: dict) -> int:
    output = context.get("output", [])
    text = output[0]["text"] if output else ""
    return min(10, max(2, 2 + len(text) // 500))

@mcp.tool(name="summarize", description="Summarize text", credits=price_by_length)
async def summarize(text: str) -> str:
    return f"Summary of {len(text)} characters..."
```

> "The callable receives a context dict AFTER the tool executes. It has three keys: `args`, `result`, and `request`. So you can price based on what actually happened."

#### Step 4: Add a resource and prompt

```python
@mcp.resource("data://reports/latest", name="Latest Report", credits=5)
async def latest_report() -> dict: ...

@mcp.prompt(name="analyze", description="Generate analysis prompt", credits=1)
def analyze_prompt(topic: str) -> list:
    return [{"role": "user", "content": {"type": "text", "text": f"Analyze: {topic}"}}]
```

> "Resources are data endpoints by URI. Prompts return message lists. All three primitives support credit pricing."

#### Step 5: Start

```python
async def main():
    result = await mcp.start(port=3000)
    info = result["info"]
    print(f"MCP server running at {info['baseUrl']}/mcp")
```

> "`mcp.start()` returns a dict with `info` and `stop`. The info has the base URL and registered tools. Call `await stop()` for graceful shutdown."

**Run it:**
```bash
python server.py
# → MCP server running at http://localhost:3000/mcp
```

---

### Section 3: TypeScript MCP Server (10 min)

**Open `ts/server.ts`**

> "TypeScript uses an imperative API instead of decorators."

```typescript
payments.mcp.registerTool(
  "search",
  { title: "Search", description: "Search the web", inputSchema: z.object({...}) },
  async (args) => ({ content: [{ type: "text", text: `Results for: ${args.query}` }] }),
  { credits: 1n },
);
```

**Key differences from Python:**
- `payments.mcp.registerTool()` instead of `@mcp.tool()`
- Credits use BigInt: `1n`, `5n`
- Dynamic credits: `credits: (ctx) => BigInt(...)` — callback receives context after execution
- `payments.mcp.registerResource()` and `payments.mcp.registerPrompt()` for other primitives
- `payments.mcp.start({port, agentId, baseUrl, serverName, ...})` — options object instead of keyword args

> "Different syntax, same concepts. Both produce identical MCP endpoints."

---

### Section 4: Testing with the Client (10 min)

**Open `python/client.py`**

> "The client gets an x402 token and sends it as a Bearer token in a JSON-RPC request. Note: the client uses `NVM_SUBSCRIBER_API_KEY` — a subscriber key, not the builder key the server uses."

```python
import urllib3
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

payments = Payments.get_instance(
    PaymentOptions(
        nvm_api_key=os.getenv("NVM_SUBSCRIBER_API_KEY", ""),
        environment=os.getenv("NVM_ENVIRONMENT", "sandbox"),
    )
)

token_result = payments.x402.get_x402_access_token(PLAN_ID)
access_token = token_result["accessToken"]

with httpx.Client(timeout=60.0) as client:
    response = client.post(
        f"{SERVER_URL}/mcp",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {access_token}",
        },
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search", "arguments": {"query": "climate data"}},
            "id": 1,
        },
    )

result = response.json()
print("Content:", result.get("result", {}).get("content"))    # Tool output
print("Payment:", result.get("result", {}).get("_meta"))       # Settlement receipt
```

> "A few things to call out: we use `httpx.Client(timeout=60.0)` — the default 5-second timeout is too short for payment verification. The `Accept` header includes both `application/json` and `text/event-stream` because MCP streamable HTTP may respond with either. And the response includes your tool output plus a `_meta` field with payment metadata."

**Run it:**
```bash
# Terminal 1: server is already running
# Terminal 2:
python client.py
# → Content: [{"type": "text", "text": "Results for: climate data"}]
# → Payment: {"txHash": "...", "creditsRedeemed": 1, ...}
```

**Show TypeScript client (`ts/client.ts`):**
- Same flow with `fetch` and `getX402AccessToken()`
- Identical JSON-RPC structure

---

### Section 5: Dynamic Pricing + Observability (10 min)

**Dynamic pricing recap:**

> "We already saw the `price_by_length` function. The key insight: the callable runs AFTER the tool executes. So you charge based on actual output, not estimated output."

**Observability (mention, don't demo unless time permits):**

> "If your tool calls an LLM, add a `paywall_context` parameter. The framework injects subscriber identity and request metadata. Use `StartAgentRequest` + `payments.observability.with_openai()` to get a proxied OpenAI client that tags every LLM call with the subscriber. Your Helicone dashboard shows exactly which subscriber caused which LLM costs."

**Connecting AI Assistants (quick mention):**

> "Once your server runs, Claude Code and Cursor can connect directly. Add your `/mcp` endpoint to the MCP settings. The AI assistant auto-discovers tools via `tools/list` and uses them with payment tokens."

```json
{
  "mcpServers": {
    "my-server": { "url": "http://localhost:3000/mcp" }
  }
}
```

---

## Troubleshooting Notes (for presenter)

| Issue | Fix |
|-------|-----|
| `PaymentsMCP` import fails | Check `payments-py` is up to date: `pip install -U payments-py` |
| `Payments()` constructor error | Use `Payments.get_instance(PaymentOptions(...))` — not `Payments(...)` directly |
| `mcp.start()` fails | Check port 3000 is free; check `NVM_AGENT_ID` is set |
| Client gets 401/403 | Token must be sent as `Authorization: Bearer <token>`, not `payment-signature`. Also verify client uses `NVM_SUBSCRIBER_API_KEY` (subscriber key), not the builder `NVM_API_KEY` |
| Client timeout / connection error | Use `httpx.Client(timeout=60.0)` — the default 5s timeout is too short for payment verification round-trips |
| Client gets empty or unexpected response | Add `Accept: application/json, text/event-stream` header — MCP streamable HTTP requires it |
| `.env` not loading | Add `from dotenv import load_dotenv` and call `load_dotenv()` at the top of every file |
| SSL warnings flooding console | Add `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)` at the top |
| Dynamic pricing returns wrong amount | Check the context dict structure: `context.get("output")` vs `context.get("result")` — depends on version |
| TypeScript `registerTool` type errors | Use `as any` for inputSchema if zod types don't match |
| `_meta` field missing in response | Check server is using PaymentsMCP (not plain MCP) |

---

## Backup Plan

If the MCP server won't start:
1. **Walk through the code** — explain each decorator/registration call
2. **Use curl to simulate** — send JSON-RPC to a pre-running server
3. **Show the Agent Card from `agents/mcp-server-agent/`** — a more complete reference implementation
