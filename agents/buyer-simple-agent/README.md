# Data Buying Agent

A Strands AI agent that **discovers sellers, purchases data via x402 payments, and tracks spending** with budget management.

This is the buyer counterpart to the [seller-simple-agent](../seller-simple-agent/). Together they demonstrate a complete autonomous data marketplace.

## Architecture

```
┌─────────────────────────────────────────────┐
│            Strands Agent Core               │
│                                             │
│  ┌──────────────────┐  ┌─────────────────┐  │
│  │ discover_pricing │  │ check_balance   │  │
│  │  (GET /pricing)  │  │ (NVM API +      │  │
│  │                  │  │  local budget)  │  │
│  └──────────────────┘  └─────────────────┘  │
│           ┌─────────────────┐               │
│           │ purchase_data   │               │
│           │ (x402 token +   │               │
│           │  POST /data)    │               │
│           └─────────────────┘               │
└──────────────┬──────────────┬───────────────┘
               │              │
    ┌──────────▼──┐   ┌──────▼──────────┐
    │  CLI Agent  │   │  AgentCore      │
    │  + OpenAI   │   │  + Bedrock      │
    │  (local)    │   │  (AWS)          │
    └─────────────┘   └─────────────────┘
```

## Quick Start

```bash
# Install dependencies
poetry install

# Copy environment file and fill in your credentials
cp .env.example .env

# Start the seller (in another terminal)
cd ../seller-simple-agent && poetry run agent

# Run the interactive agent
poetry run agent

# Or run the scripted demo (no LLM needed)
poetry run client

# Or run the web server with React frontend
poetry run python -m src.web
```

## How It Works

```
Buyer Agent                    Nevermined                    Seller Agent
     │                            │                              │
     │  1. GET /pricing           │                              │
     │───────────────────────────────────────────────────────────>│
     │  <- pricing tiers          │                              │
     │<───────────────────────────────────────────────────────────│
     │                            │                              │
     │  2. Check balance          │                              │
     │───────────────────────────>│                              │
     │  <- credits remaining      │                              │
     │<───────────────────────────│                              │
     │                            │                              │
     │  3. Get x402 access token  │                              │
     │───────────────────────────>│                              │
     │  <- access token           │                              │
     │<───────────────────────────│                              │
     │                            │                              │
     │  4. POST /data + token     │                              │
     │───────────────────────────────────────────────────────────>│
     │                            │  5. Verify & settle          │
     │                            │<─────────────────────────────│
     │                            │  <- settlement receipt       │
     │                            │─────────────────────────────>│
     │  <- data response          │                              │
     │<───────────────────────────────────────────────────────────│
```

## Tools

### HTTP Mode (x402)

| Tool | Description | Credits |
|------|-------------|---------|
| `discover_pricing` | GET /pricing from seller — shows tiers and costs | Free |
| `check_balance` | Check NVM credit balance + local budget status | Free |
| `purchase_data` | Generate x402 token, POST /data, return results | Varies by tier |

### A2A Mode (Agent-to-Agent)

| Tool | Description | Credits |
|------|-------------|---------|
| `discover_agent` | Fetch /.well-known/agent.json — agent card + payment info | Free |
| `check_balance` | Check NVM credit balance + local budget status | Free |
| `purchase_a2a` | Send A2A message with auto-payment via PaymentsClient | Varies by tool |

**Key difference from seller:** Buyer tools are plain `@tool` — NOT `@requires_payment`. The buyer *generates* payment tokens; it doesn't receive them.

## Deployment Modes

### 1. Interactive CLI (local development)

```bash
poetry run agent                        # A2A mode (default)
poetry run python -m src.agent --mode http  # HTTP/x402 mode
```

Uses OpenAI for the LLM. The agent runs a read-eval-print loop where you type queries and it orchestrates the buyer tools.

### 2. Web Server + React Frontend

```bash
poetry run python -m src.web                # Starts on http://localhost:8000

# In a separate terminal for dev mode:
cd frontend && npm install && npm run dev   # Opens http://localhost:5173
```

The web server exposes JSON APIs (`/api/chat`, `/api/sellers`, `/api/balance`, `/api/logs/stream`) and the React frontend provides a chat UI with a seller sidebar and activity log.

### 3. Scripted Demo (no LLM)

```bash
poetry run client
```

Step-by-step x402 buyer flow calling tools directly — no LLM needed. Good for testing the payment flow.

### 4. Strands Demo (LLM-orchestrated)

```bash
poetry run demo
```

Pre-scripted prompts that exercise all buyer tools with LLM orchestration.

### 5. A2A Client Demo

```bash
poetry run client-a2a
```

Step-by-step A2A buyer flow: fetch agent card, parse payment, send A2A message, get response. Requires the seller running in A2A mode (`poetry run agent-a2a`).

### 6. AWS AgentCore

Deploy the buyer to AgentCore for production use with SigV4-signed requests and Bedrock LLM inference.

```bash
# Install with AgentCore extras
poetry install -E agentcore

# Local test (AgentCore-compatible mode)
poetry run web-agentcore

# Deploy to AgentCore
agentcore init    # Interactive setup (entry point: src/web_agentcore.py)
agentcore deploy  # Build, push, and deploy
```

**Key differences from local mode:**
- Uses `AgentCorePaymentsClient` with SigV4 signing for cross-agent requests
- Sends payment tokens in both standard and AgentCore-prefixed headers (proxy strips standard ones)
- Pre-registers the seller from `SELLER_AGENT_ARN` (agent card discovery doesn't work through AgentCore's proxy)
- Rewrites `/invocations` → `/api/chat` (AgentCore routes all traffic to `/invocations`)

**Required env vars (in addition to standard ones):**

| Variable | Description |
|----------|-------------|
| `SELLER_AGENT_ARN` | The seller agent's AgentCore runtime ARN |
| `AWS_REGION` | AWS region (default: `us-west-2`) |

**Key files:**
- `src/web_agentcore.py` — AgentCore entry point (seller pre-registration + path rewrite)
- `src/agentcore_payments_client.py` — SigV4 signing + dual headers + URL handling

See [Deploy to AgentCore](../../docs/deploy-to-agentcore.md) for the full walkthrough.

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NVM_API_KEY` | Yes | Nevermined **subscriber** API key |
| `NVM_ENVIRONMENT` | Yes | `sandbox`, `staging_sandbox`, or `live` |
| `NVM_PLAN_ID` | Yes | The seller's plan ID you subscribed to |
| `NVM_AGENT_ID` | No | Seller's agent ID (for token scoping) |
| `SELLER_URL` | No | Seller HTTP endpoint (default: `http://localhost:3000`) |
| `SELLER_A2A_URL` | No | Seller A2A endpoint (default: `http://localhost:9000`) |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*not needed for `client`) |
| `MODEL_ID` | No | OpenAI model (default: `gpt-4o-mini`) |
| `MAX_DAILY_SPEND` | No | Daily credit limit (0 = unlimited) |
| `MAX_PER_REQUEST` | No | Per-request credit limit (0 = unlimited) |

### Subscribing to a Seller's Plan

Before buying data, you need to subscribe to the seller's plan:

1. Get the seller's **Plan ID** (from their `/pricing` endpoint or the Nevermined App)
2. Go to [nevermined.app](https://nevermined.app) and find the plan
3. Subscribe (purchase credits)
4. Set `NVM_PLAN_ID` in your `.env` to the seller's plan ID
5. Use your **subscriber** API key as `NVM_API_KEY`

## Multi-Agent Demo (CLI)

This walkthrough demonstrates the full A2A marketplace flow — starting with no sellers, adding them incrementally, discovering capabilities, and making purchases.

### Prerequisites

Set up both agents:

```bash
# Buyer
cd agents/buyer-simple-agent
poetry install
cp .env.example .env  # fill in credentials

# Seller
cd agents/seller-simple-agent
poetry install
cp .env.example .env  # fill in credentials (NVM_AGENT_ID required)
```

> **Note:** Use `poetry run python -m src.<module>` to run entry points (not `poetry run agent`) because both projects use `package-mode = false`.

### Step-by-Step (3 Terminals)

**Terminal 1 — Start the Buyer Agent:**

```bash
cd agents/buyer-simple-agent
poetry run python -m src.agent
```

The buyer starts in A2A mode with a registration server on port 8000. Ask `What sellers are available?` — it will say "No sellers registered yet."

**Terminal 2 — Start Seller A (search only):**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools search --port 9001 --buyer-url http://localhost:8000
```

Seller A starts with only the `search` tool (1 credit) and auto-registers with the buyer. Terminal 1 will log the registration.

**Back in Terminal 1:**

- `What sellers are available?` — Now shows 1 seller with Web Search skill
- `Tell me more about the Data Selling Agent` — Fetches the full agent card
- `Search for what is bitcoin` — Purchases data (1 credit), see results in both terminals
- `Check my balance` — Shows remaining credits and daily budget

**Terminal 3 — Start Seller B (summarize):**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools summarize --port 9002 --buyer-url http://localhost:8000
```

Seller B starts with the `summarize` tool (5 credits). Now the buyer sees 2 sellers.

**Back in Terminal 1:**

- `What sellers are available now?` — Lists both sellers
- `Use the seller on port 9002 to summarize the latest AI trends` — Purchases from Seller B (5 credits)

### Seller CLI Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--tools` | Comma-separated tools to expose (`search`, `summarize`, `research`) | `--tools search` |
| `--port` | Port to run on (default: 9000) | `--port 9001` |
| `--buyer-url` | Buyer URL to auto-register with | `--buyer-url http://localhost:8000` |

## Web UI Demo

This walkthrough uses the React frontend instead of the CLI. Open **4 terminals**.

### Step 1 — Start Backend + Frontend

**Terminal 1 (Backend):**

```bash
cd agents/buyer-simple-agent
poetry run python -m src.web
```

**Terminal 2 (Frontend):**

```bash
cd agents/buyer-simple-agent/frontend
npm install && npm run dev
```

Open **http://localhost:5173** — you'll see the chat interface with an empty seller sidebar and activity log.

### Step 2 — Start Sellers

**Terminal 3 (Seller A — search, 1 credit):**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools search --port 9001 --buyer-url http://localhost:8000
```

**Terminal 4 (Seller B — summarize, 5 credits):**

```bash
cd agents/seller-simple-agent
poetry run python -m src.agent_a2a --tools summarize --port 9002 --buyer-url http://localhost:8000
```

The sidebar updates automatically as sellers register.

### Step 3 — Interact

Type in the chat input:

- `What sellers are available?` — Lists sellers with skills and pricing
- `Search for what is bitcoin` — Purchases from Seller A (1 credit)
- `Check my balance` — Shows credits and budget
- `Use the seller on port 9002 to summarize the latest AI trends` — Purchases from Seller B (5 credits)

The activity log panel shows real-time events (registrations, payments, completions).

### API Endpoints

The web server exposes these endpoints for programmatic access:

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/api/sellers` | List registered sellers | JSON array |
| `GET` | `/api/balance` | Credit balance and budget | JSON object |
| `POST` | `/api/chat` | Chat with the agent (SSE stream) | `text/event-stream` |
| `GET` | `/api/logs/stream` | Activity log stream (SSE) | `text/event-stream` |

## Seller vs Buyer Comparison

| Aspect | Seller | Buyer |
|--------|--------|-------|
| Entry point | FastAPI server (port 3000) or A2A (port 9000) | Interactive CLI |
| Tools | `@requires_payment` protected | Plain `@tool` |
| NVM_API_KEY | Builder/seller key | Subscriber key |
| NVM_PLAN_ID | "My plan I created" | "The seller's plan I subscribe to" |
| Payments SDK | Verify + settle tokens | Generate tokens + check balance |
| Tracking | Analytics (earnings) | Budget (spending limits) |
| SELLER_URL | N/A (is the server) | Required (where to buy from) |

## Customization Ideas

1. **Multi-provider comparison** — Query multiple sellers, compare results and prices
2. **Auto-subscribe** — Call `payments.plans.order_plan()` if not yet subscribed
3. **Quality scoring** — Track data quality per seller over time
4. **Caching** — Cache results to avoid duplicate purchases
5. **A2A protocol** — Already supported! Use `discover_agent` + `purchase_a2a` tools
6. **Persistent budget** — Store budget in file/database instead of in-memory

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `NVM_API_KEY is required` | Create `.env` with your Nevermined API key |
| `NVM_AGENT_ID is required` | Seller needs `NVM_AGENT_ID` in `.env` (find in Nevermined App agent settings) |
| `OPENAI_API_KEY is required` | Add your OpenAI key to `.env` |
| Seller registration fails | Ensure buyer is running on port 8000 before starting sellers |
| `poetry run agent` fails | Use `poetry run python -m src.agent` instead (`package-mode = false`) |
| CLI doesn't show A2A tools | A2A mode is the default; use `--mode http` only if you want direct x402 |
| Credits not decreasing | Check `NVM_ENVIRONMENT=sandbox` and that plan has credits |
| `No file/folder found for package` | Run `poetry install` in the agent directory |
| Frontend shows blank page | Ensure `npm run dev` is running in `frontend/` dir |
| CORS errors in browser | Ensure buyer backend is on port 8000 (CORS allows localhost:5173) |
| Activity log empty | Open `http://localhost:5173` (not 8000) for dev mode |

## Related

- [seller-simple-agent](../seller-simple-agent/) — The seller counterpart
