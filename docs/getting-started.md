# Getting Started

This guide will help you set up your development environment and run your first payment-enabled AI agent.

## Prerequisites

- **Python 3.10+**
- **Poetry** for dependency management
- **Git** for cloning the repository

## Step 1: Get Your Nevermined API Key

1. Open [https://nevermined.app/](https://nevermined.app/) and sign in with your account
2. Navigate to **API Keys** > **Global NVM API Keys**
3. Click **+ New API Key**
4. Give your key a descriptive name, select the permissions you need, and click **Generate API Key**
5. Click **Copy Key** to copy it to your clipboard and store it securely

> **Note:** API keys are environment-specific. Sandbox keys begin with `sandbox:` and live keys start with `live:`. Keep your API key secure — don't commit it to version control or share it publicly.

## Step 2: Create a Payment Plan

A payment plan controls how users pay to access your agent.

1. In the Nevermined App, click **"Create Agent"** or **"My Pricing Plans"**
2. Fill in your agent metadata (name, description)
3. **Register API Endpoints**: Add the endpoints you want to protect
   - For HTTP agents: `POST /ask`, `GET /data`, etc.
   - For MCP: Use logical URLs like `mcp://my-agent/tools/my-tool`
4. Create a payment plan:
   - **Credit-based**: Pay per request (recommended for getting started)
   - **Time-based**: Pay for access period
   - **Trial**: Free trial for testing
5. Copy your **Plan ID** from the plan details

## Step 3: Set Up Your Environment

```bash
# Clone the repository
git clone https://github.com/nevermined-io/hackathons.git
cd hackathons
```

## Step 4: Choose an Agent

Each agent is in the `agents/` directory with its own dependencies and `.env.example`:

| Agent | What it does | Run command |
|-------|-------------|-------------|
| [Buyer Agent](../agents/buyer-simple-agent/) | Discovers sellers, purchases data, tracks spending | `poetry run python -m src.agent` |
| [Seller Agent](../agents/seller-simple-agent/) | Sells data/services with tiered pricing | `poetry run python -m src.agent` |
| [MCP Server](../agents/mcp-server-agent/) | Payment-protected MCP tools | `poetry run python -m src.server` |
| [Strands Agent](../agents/strands-simple-agent/) | Strands SDK with payment tools | `poetry run python agent.py` |

Example — running the seller agent:

```bash
cd agents/seller-simple-agent
poetry install
cp .env.example .env
# Edit .env with your credentials

poetry run python -m src.agent
```

> **Note:** All agents use `package-mode = false`, so use `poetry run python -m src.<module>` (not `poetry run agent`).

## Step 5: Test Your Agent

In a new terminal, run the client:

```bash
poetry run python -m src.client
```

You should see:

1. **402 Payment Required** — First request without token
2. **Token generation** — Client gets x402 access token
3. **200 OK** — Second request with token succeeds

## Understanding the x402 Flow

```
┌─────────┐                              ┌─────────┐
│  Client │                              │  Agent  │
└────┬────┘                              └────┬────┘
     │                                        │
     │  1. POST /ask (no token)               │
     │───────────────────────────────────────>│
     │                                        │
     │  2. 402 Payment Required               │
     │     Header: payment-required           │
     │<───────────────────────────────────────│
     │                                        │
     │  3. Generate x402 token via SDK        │
     │                                        │
     │  4. POST /ask                          │
     │     Header: payment-signature          │
     │───────────────────────────────────────>│
     │                                        │
     │  5. 200 OK + response                  │
     │     Header: payment-response           │
     │<───────────────────────────────────────│
```

## Next Steps

1. **Customize your agent** — Modify the business logic
2. **Add more endpoints** — Protect additional routes
3. **Deploy to AWS** — See [AWS Integration](./aws-integration.md) and [Deploy to AgentCore](./deploy-to-agentcore.md)
4. **Run the multi-agent demo** — See the [Buyer Agent README](../agents/buyer-simple-agent/) for a full buyer-seller marketplace walkthrough

## Troubleshooting

### "NVM_API_KEY is required"

Make sure your `.env` file exists and contains valid credentials.

### "402 Payment Required" keeps failing

1. Verify your `NVM_PLAN_ID` is correct
2. Check that you have credits in your plan
3. Ensure the endpoint URL matches your plan configuration

### "Invalid token"

1. Tokens expire — generate a new one
2. Check that you're using the correct plan ID

## Resources

- [Nevermined Documentation](https://nevermined.ai/docs)
- [x402 Protocol Spec](https://github.com/coinbase/x402)
- [Support Discord](https://discord.com/invite/GZju2qScKq)
