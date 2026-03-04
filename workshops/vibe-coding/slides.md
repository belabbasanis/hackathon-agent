---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    font-family: 'Helvetica Neue', Arial, sans-serif;
  }
  section.title {
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.title h1 {
    font-size: 2.5em;
  }
  code {
    font-size: 0.85em;
  }
  table {
    font-size: 0.8em;
  }
  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5em;
  }
---

<!-- _class: title -->

# Vibe Coding with Nevermined

### Build a Payment-Protected AI Agent from Scratch

Using Claude Code + AI Skill + MCP Server

<!--
Welcome everyone! Today we're going to build a fully monetized AI agent from scratch — using nothing but natural language and Claude Code. No copy-pasting from docs, no boilerplate templates. Just describe what you want, and watch it get built.
-->

---

# Supercharging Vibe Coding

We give Claude Code **two layers of Nevermined knowledge:**

| Layer | What it is | Strength |
|-------|-----------|----------|
| **AI Skill** | Local knowledge files Claude reads instantly | Fast, offline, consistent patterns |
| **MCP Server** | Live connection to docs.nevermined.app | Always up-to-date, full coverage |

**Analogy:**
- Skill = A developer who **memorized** the SDK
- MCP = Having the **docs open** in a browser tab
- Both = A Nevermined expert who can also look things up

<!--
Think of it like this. The AI Skill is a curated knowledge base — common patterns, middleware setup for every framework, troubleshooting guides. It's installed locally so it's fast and works offline.

The MCP server is a live connection to the full documentation. If Claude needs to look up a niche API method or the latest release notes, it queries the live docs.

Together, they make Claude a Nevermined expert. This is what we'll set up now.
-->

---

# What is Nevermined? (60 seconds)

**Monetize your AI agents with 3 lines of code**

- x402 = HTTP payment protocol (like 401 but for payments)
- Client calls your agent → gets **402 Payment Required** → pays → retries → done
- Works with **crypto** (on-chain credits) or **fiat** (Stripe cards)
- SDKs for **TypeScript** and **Python**

The developer experience:

```python
# Just add this middleware — that's it
app.add_middleware(PaymentMiddleware, payments=payments,
    routes={"POST /ask": {"plan_id": PLAN_ID, "credits": 1}})
```

<!--
Nevermined lets you monetize AI agents. Your agent does useful work — search, analysis, content generation — and Nevermined handles the payments. Users pay per request using the x402 protocol, which works over standard HTTP headers.

The key selling point: it's one line of middleware. You don't need to build a billing system, handle Stripe webhooks, or manage subscriptions. The middleware does everything.
-->

---

# Before & After

<div class="columns">
<div>

### Without Nevermined (free)

```python
@app.post("/ask")
def ask(query: str):
    return {"answer": do_work(query)}
```

Anyone can call it.
No revenue.

</div>
<div>

### With Nevermined (paid)

```python
app.add_middleware(
    PaymentMiddleware,
    payments=payments,
    routes={
        "POST /ask": {
            "plan_id": PLAN_ID,
            "credits": 1
        }
    },
)

@app.post("/ask")
def ask(query: str):
    return {"answer": do_work(query)}
```

Pay-per-request. Automatic settlement.

</div>
</div>

<!--
Look at the difference. Your business logic — the /ask endpoint — doesn't change at all. You just wrap it with the payment middleware. That middleware handles the 402 response, token verification, and credit settlement. Your endpoint only runs when the payment is valid.
-->

---

# Setup Step 1: Install the AI Skill

```bash
mkdir -p ~/.claude/skills

tmpdir="$(mktemp -d)"
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/nevermined-io/docs "$tmpdir"
cd "$tmpdir"
git sparse-checkout set skills/nevermined-payments
cp -R skills/nevermined-payments ~/.claude/skills/
cd - && rm -rf "$tmpdir"
```

**What gets installed:**
`~/.claude/skills/nevermined-payments/skill.md`

Claude Code **auto-discovers** it — no config file needed.

Contains: SDK patterns, middleware setup, x402 flows, troubleshooting

<!--
Let's do this live. This one-liner clones just the skill folder from the Nevermined docs repo and copies it into Claude Code's skills directory. Claude Code automatically discovers any skill files in this directory — no configuration needed.

The skill contains structured knowledge about every Nevermined integration pattern: Express, FastAPI, Strands, MCP, A2A. It's like giving Claude a Nevermined certification.
-->

---

# Setup Step 2: Connect the MCP Server

**Quick setup (one command):**

```bash
claude mcp add nevermined --transport http https://docs.nevermined.app/mcp
```

Or manually add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "nevermined": {
      "url": "https://docs.nevermined.app/mcp"
    }
  }
}
```

<!--
Now let's add the live documentation layer. This config tells Claude Code to connect to the Nevermined docs MCP server at startup. You can use the one-liner or manually edit the settings file.

To verify: ask Claude a common question like "How do I protect a FastAPI endpoint with Nevermined?" — it answers instantly from the Skill. Then ask something specific like "What are the exact parameters for CardDelegationConfig?" — it queries the MCP server. Both layers working together.

Pro tip for the hackathon: if the WiFi goes down, the skill still works. It's local files.
-->

---

# Setup Step 3: Get Your Nevermined Credentials

### 1. Get an API Key
1. Go to **nevermined.app** → Sign in
2. **Settings** → **API Keys** → **Global NVM API Keys**
3. **+ New API Key** → Copy (starts with `sandbox:`)

### 2. Create a Payment Plan
1. **My Agents** → **New Agent** → Fill metadata
2. Create a **credit-based plan** (e.g. 100 credits for 1 USDC)
3. Copy the **Plan ID**

<!--
Before we code, we need two things from Nevermined: an API key and a payment plan.

The API key identifies you as a builder. It's environment-specific — sandbox keys start with 'sandbox:' and work on the test network, so no real money involved.

The plan defines how users pay for your agent. When users subscribe to this plan, they get credits. Each request to your agent costs some credits. Let me show you how to create these in the Nevermined app.
-->

---

# Setup Step 4: Configure Your Environment

```bash
NVM_API_KEY=sandbox:your-key-here
NVM_PLAN_ID=plan_xxx
NVM_ENVIRONMENT=sandbox
OPENAI_API_KEY=sk-xxx
```

Copy these into a `.env` file in your project root.

<!--
Create a .env file with your credentials. The NVM_API_KEY and NVM_PLAN_ID come from the previous step. The environment should be sandbox for testing. And you'll need an OpenAI key for the LLM calls in our agent.
-->

---

<!-- _class: title -->

# Live Build

### Let's build a payment-protected agent
### from an empty directory

<!--
Now the fun part. I have an empty directory. I have Claude Code with the Nevermined skill and MCP server. Let's see how fast we can build a fully monetized AI agent.

I'm going to describe what I want in natural language, and Claude Code will write all the code. Watch how it uses the Nevermined SDK patterns from the skill without me having to look up anything.
-->

---

# Prompt 1: Project Setup

```
I want to build a Python FastAPI agent that answers questions
about technology trends. It should be protected with Nevermined
x402 payments. Use the payments_py SDK with FastAPI middleware.
Set up a poetry project with the right dependencies.
```

**Claude creates:**
- `pyproject.toml` with `payments-py[fastapi]`, `fastapi`, `uvicorn`, `openai`
- Basic project structure
- `.env` loading with `python-dotenv`

> Notice: Claude gets the exact package names from the Skill — no hallucination.

<!--
Watch this. I describe what I want at a high level and Claude sets up the entire project structure. It knows the exact package name is payments-py with the fastapi extra — that comes from the skill, not from guessing.

If I had asked for TypeScript, it would use @nevermined-io/payments with the express middleware instead. The skill knows both languages.
-->

---

# Prompt 2: Core Agent

```
Create the main agent file:
1. Initialize Nevermined Payments from environment variables
2. Add x402 PaymentMiddleware for POST /ask (1 credit)
3. /ask takes JSON body with "query" field
4. Use OpenAI to generate an answer
5. Add GET /health (unprotected)
6. Run on port 8000
```

**Claude writes the complete agent** using the correct:
- `Payments.get_instance()` pattern
- `PaymentMiddleware` import path
- Route configuration format

<!--
Here's where the skill really shines. Claude knows the exact initialization pattern — Payments.get_instance with PaymentOptions — and the correct middleware import path. It knows the route config format is a dictionary with plan_id and credits. All from the skill, instantly, no network call.

Let me run this prompt now and we'll see what Claude generates.
-->

---

# The Generated Agent — Setup

```python
from fastapi import FastAPI, Request
from payments_py import Payments, PaymentOptions
from payments_py.x402.fastapi import PaymentMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

payments = Payments.get_instance(PaymentOptions(
    nvm_api_key=os.getenv("NVM_API_KEY"),
    environment=os.getenv("NVM_ENVIRONMENT", "sandbox"),
))

app = FastAPI()
app.add_middleware(PaymentMiddleware, payments=payments,
    routes={"POST /ask": {"plan_id": os.getenv("NVM_PLAN_ID"), "credits": 1}})

client = OpenAI()
```

Imports, Nevermined init, and **one line** of payment middleware.

<!--
Here's the first half of what Claude generated. Standard imports, Payments initialization from env vars, and the middleware protecting POST /ask for 1 credit per request. Notice the middleware config: a dictionary mapping route patterns to plan ID and credit cost. That's the entire payment integration.
-->

---

# The Generated Agent — Endpoints

```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
async def ask(request: Request):
    body = await request.json()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a tech trends analyst."},
            {"role": "user", "content": body["query"]},
        ],
    )
    return {"answer": resp.choices[0].message.content}
```

Your business logic doesn't change — the middleware handles all payment flow.

<!--
Bottom half: the actual business logic — a health check and the /ask endpoint with a simple OpenAI call. This is YOUR code. Everything in the previous slide is Nevermined plumbing. Your endpoint only runs when the payment is valid.
-->

---

# Prompt 3: Build a Client

```
Create a client script that:
1. Calls /ask WITHOUT a token (should get 402)
2. Parses the 402 response to show payment requirements
3. Gets an x402 access token using the payments SDK
4. Retries with the token
5. Shows the response and credits used
```

**This demonstrates the full x402 flow:**
```
No token  → 402 Payment Required
Get token → payment-signature header
Retry     → 200 OK + answer + receipt
```

<!--
Now let's build a client to test it. I want to show the full payment cycle — first a request without payment that gets rejected, then the payment flow, then the successful request.

This is exactly what your users or other agents will do when they call your agent for the first time: discover the pricing, pay, and get served.
-->

---

# Testing It Live

### Start the agent
```bash
poetry install
poetry run uvicorn agent:app --port 8000
```

### Test the flow
```bash
# Health check (free)
curl http://localhost:8000/health

# Ask without payment → 402
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Future of autonomous agents?"}' -v
```

```bash
# Run the client (full payment flow)
poetry run python client.py
```

<!--
Let's fire it up. Start the agent, then test it. Health check works without payment. An ask request without a token gets 402 Payment Required. Finally, the client script does the full flow: gets a token, retries with it, and shows the answer plus credits used.
-->

---

# What Just Happened

```
0:00  Empty directory
0:03  Project scaffolded (pyproject.toml, structure)
0:10  Agent code written (FastAPI + x402 middleware)
0:15  Client code written (full payment flow)
0:18  Installed + running
0:20  First paid request settled
```

**20 minutes from nothing to a monetized AI agent.**

No docs were read. No boilerplate was copied.
Claude Code + AI Skill + MCP Server = Vibe Coding.

<!--
Let's recap what just happened. In about 20 minutes, we went from an empty directory to a fully functioning, payment-protected AI agent. Claude Code wrote all the code — the project setup, the agent, the client, even the error handling.

The Nevermined skill gave it instant recall of SDK patterns. The MCP server was available for any edge cases. We never opened the documentation once. That's vibe coding.
-->

---

# Your Turn

### Get started in 60 seconds:

1. **Install the Skill** (one-liner from setup slide)

2. **Connect the MCP Server:**
   ```bash
   claude mcp add nevermined --transport http https://docs.nevermined.app/mcp
   ```

3. **Pick a starter kit** from the hackathon repo and start prompting!

<!--
Now it's your turn. Install the skill and MCP server — takes 60 seconds. Pick one of the starter kit READMEs as inspiration. Then open Claude Code and just start describing what you want to build. Let Claude and Nevermined do the heavy lifting. We're here if you get stuck.
-->

---

# Resources

| | |
|---|---|
| Nevermined Docs | docs.nevermined.app |
| AI Skill Guide | nevermined.ai/docs/development-guide/build-using-nvm-skill |
| MCP Server | docs.nevermined.app/mcp |
| Hackathon Kits | `starter-kits/` in this repo |
| Discord | discord.com/invite/GZju2qScKq |
