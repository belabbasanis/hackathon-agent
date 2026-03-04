# Workshop 1: Nevermined + Claude Code + Vibe Coding

**Duration:** 1 hour
**Goal:** Participants build a payment-protected AI agent from scratch using Claude Code with the Nevermined AI Skill + MCP server — "vibe coding" style.

---

## Format Recommendation

| Element | Recommendation |
|---------|----------------|
| **Slides** | Minimal — 5-6 slides max for intro/context only |
| **Live demo** | Primary format — code live with Claude Code |
| **Docs site** | Have `docs.nevermined.app` open as reference |
| **Terminal** | Full-screen terminal for the live coding portion |

**Why mostly live demo:** The whole point of "vibe coding" is showing how fast you can build with AI assistance. Slides would undermine the message. Let them see it happen in real time.

---

## Pre-Workshop Checklist

### Your machine (presenter)

- [ ] Claude Code installed and working
- [ ] Nevermined AI Skill installed (`~/.claude/skills/nevermined-payments/`)
- [ ] Nevermined MCP server configured in Claude Code settings (`.claude/settings.json`)
- [ ] Valid `NVM_API_KEY` (sandbox) in environment or `.env`
- [ ] `OPENAI_API_KEY` set (for agent LLM calls)
- [ ] Poetry and Node.js installed
- [ ] A fresh empty directory ready for live coding
- [ ] Terminal font size large enough for projection (24pt+)
- [ ] Second monitor or split screen for docs.nevermined.app

### Participant machines

- [ ] Claude Code installed (or Max/Pro subscription with Claude Code access)
- [ ] Nevermined AI Skill installed (instructions will be shown during workshop)
- [ ] Nevermined account created at https://nevermined.app
- [ ] API key generated (sandbox)
- [ ] Python 3.11+ and Poetry installed (or Node.js 18+ and Yarn)

---

## Agenda

| Time | Section | Format |
|------|---------|--------|
| 0:00 - 0:05 | Welcome & What is Vibe Coding | Slides |
| 0:05 - 0:10 | What is Nevermined + x402 (30-second pitch) | Slides |
| 0:10 - 0:18 | Setting up: AI Skill + MCP Server | Live demo |
| 0:18 - 0:23 | Getting your API key + creating a payment plan | Live demo (nevermined.app) |
| 0:23 - 0:48 | Live Build: Payment-protected agent from scratch | Live coding with Claude Code |
| 0:48 - 0:55 | Testing the agent (buy credits, make requests) | Live demo |
| 0:55 - 1:00 | Q&A + Resources | Slides / open |

---

## Detailed Script

### Section 1: Welcome & What is Vibe Coding (5 min)

**[SLIDE 1: Title]**
- Workshop title, your name, Nevermined + AWS logos

**[SLIDE 2: What is Vibe Coding?]**

> "Vibe coding is when you describe what you want in natural language and an AI writes the code for you. You stay in the flow — the vibe — and the AI handles the implementation details."
>
> "Today we'll take this further. Instead of just generating code, we'll connect Claude Code to Nevermined's documentation via MCP so it actually *understands* the payment APIs. It's like giving Claude a domain expert to consult."

**Key talking points:**
- Traditional coding: read docs → write code → debug → repeat
- Vibe coding: describe intent → AI writes code with context → iterate
- We can supercharge this with two tools:
  - **AI Skill**: local knowledge files that Claude reads instantly (offline, fast)
  - **MCP Server**: live connection to documentation (always up-to-date)
- Nevermined provides both — a Claude Code skill and an MCP server at docs.nevermined.app

---

### Section 2: What is Nevermined + x402 (5 min)

**[SLIDE 3: Nevermined in 60 seconds]**

> "Nevermined lets you monetize AI agents. Your agent does useful work — search, analysis, content — and Nevermined handles the payments. Users pay per request using the x402 protocol, which works over standard HTTP headers."

**Keep this brief — just enough context:**
- x402 = HTTP payment protocol (like 401 but for payments)
- Client sends request → gets 402 → pays → retries → server settles
- Works with crypto (on-chain credits) or fiat (Stripe cards)
- SDKs available for TypeScript and Python
- 3 lines of middleware code to protect any endpoint

**[SLIDE 4: The Developer Experience]**

Show a before/after code comparison:

```python
# WITHOUT Nevermined (free endpoint)
@app.post("/ask")
def ask(query: str):
    return {"answer": do_work(query)}

# WITH Nevermined (paid endpoint — just add middleware)
app.add_middleware(PaymentMiddleware, payments=payments,
    routes={"POST /ask": {"plan_id": PLAN_ID, "credits": 1}})

@app.post("/ask")
def ask(query: str):
    return {"answer": do_work(query)}
```

> "That's it. One middleware line. The rest of the payment flow is handled for you."

---

### Section 3: Setting Up — AI Skill + MCP Server (8 min)

**[SWITCH TO TERMINAL — Claude Code]**

> "To vibe code with Nevermined, we'll give Claude Code two superpowers: a **Skill** and an **MCP server**. Think of it like this — the Skill is a cheat sheet Claude has memorized, and the MCP server is a live connection to the full documentation."

**[SLIDE 5: Skill vs MCP — Two Layers of Knowledge]**

| Layer | What it is | Strength | Analogy |
|-------|-----------|----------|---------|
| **AI Skill** | Local knowledge files installed in Claude Code | Fast, offline, consistent patterns | A developer who memorized the SDK |
| **MCP Server** | Live connection to docs.nevermined.app | Always up-to-date, full coverage | Having the docs open in a browser tab |
| **Both together** | Recommended setup | Best of both worlds | A developer who memorized the SDK AND can look things up |

> "The Skill gives Claude instant recall of common patterns — middleware setup, x402 headers, SDK initialization. The MCP server covers edge cases and the latest API changes. Together, they make Claude a Nevermined expert."

#### Step 1: Install the Nevermined AI Skill (2 min)

```bash
# One-liner to install the skill
mkdir -p ~/.claude/skills

tmpdir="$(mktemp -d)"
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/nevermined-io/docs "$tmpdir"
cd "$tmpdir"
git sparse-checkout set skills/nevermined-payments
cp -R skills/nevermined-payments ~/.claude/skills/
cd -
rm -rf "$tmpdir"
```

> "That's it. The skill is now installed at `~/.claude/skills/nevermined-payments/`. Claude Code auto-discovers it — no config file needed. It contains structured knowledge about every Nevermined integration pattern: Express, FastAPI, Strands, MCP, A2A."

**Show what got installed:**

```bash
ls ~/.claude/skills/nevermined-payments/
# skill.md  (the main knowledge file Claude reads)
```

> "This is a curated knowledge base — SDK initialization patterns, middleware setup for every framework, x402 protocol flows, troubleshooting guides. It's like giving Claude a Nevermined certification."

#### Step 2: Connect the MCP Server (1 min)

> "Now let's add the live documentation layer."

Edit `.claude/settings.json` (or use `claude mcp add`):

```json
{
  "mcpServers": {
    "nevermined": {
      "url": "https://docs.nevermined.app/mcp"
    }
  }
}
```

> "The MCP server complements the skill. If Claude needs to look up something not covered in the skill — a niche API method, the latest release notes, a specific error code — it queries the live docs."

#### Step 3: Verify both are working (2 min)

Open Claude Code and ask:

```
> How do I protect a FastAPI endpoint with Nevermined x402 payments?
```

> "Watch what happens. Claude answers immediately using the skill's patterns — it doesn't need to make a network call for this common question. The skill has this memorized."

Now ask something more specific:

```
> What are the exact parameters for CardDelegationConfig in the Python SDK?
```

> "For this more specific question, Claude might consult the MCP server to get the latest API details. You'll see it make an MCP tool call in the output. Both layers working together."

**Key point for the audience:**

> "For the hackathon, I recommend installing both. The skill gives you fast, reliable patterns for 90% of what you need. The MCP server fills in the remaining 10%. And if the WiFi goes down during the hackathon? The skill still works — it's local files."

**NOTE TO PRESENTER:** If the MCP server is slow to connect, the skill alone is enough for the live coding demo. Mention the MCP server is "a nice-to-have backup" and move on.

---

### Section 4: Getting API Key + Creating a Plan (5 min)

**[SWITCH TO BROWSER — nevermined.app]**

> "Before we code, we need two things: an API key and a payment plan."

**Step 1: Get API Key**

1. Go to https://nevermined.app
2. Sign in (or create account)
3. Navigate to **Settings** → **API Keys** → **Global NVM API Keys**
4. Click **+ New API Key**
5. Name it "hackathon-workshop"
6. Copy the key (starts with `sandbox:`)

> "This key identifies you as a builder on Nevermined. It's environment-specific — sandbox keys start with 'sandbox:' and work on the test network."

**Step 2: Create a Payment Plan**

1. Go to **My Agents** or **New Agent**
2. Fill in agent metadata:
   - Name: "Workshop Demo Agent"
   - Description: "A demo agent built during the workshop"
3. Create a **credit-based plan**:
   - Name: "Pay Per Query"
   - Price: 1 USDC (or choose a price)
   - Credits: 100
4. Copy the `planId`

> "Now we have a plan. When users subscribe, they get 100 credits. Each request to our agent will cost some of those credits."

**Step 3: Set up environment**

```bash
# Create .env file
echo "NVM_API_KEY=sandbox:your-key-here" > .env
echo "NVM_PLAN_ID=plan_xxx" >> .env
echo "NVM_ENVIRONMENT=sandbox" >> .env
echo "OPENAI_API_KEY=sk-xxx" >> .env
```

---

### Section 5: Live Build — Payment-Protected Agent (25 min)

**[SWITCH TO TERMINAL — Claude Code in an empty directory]**

> "Now the fun part. Let's build a payment-protected AI agent from scratch using nothing but natural language and Claude Code. Watch how fast this goes."

#### Phase 1: Project scaffold (3 min)

```
> I want to build a Python FastAPI agent that answers questions about technology
> trends. It should be protected with Nevermined x402 payments. Use the
> payments_py SDK with FastAPI middleware. Set up a poetry project with the
> right dependencies.
```

**What Claude should do:**
- Create `pyproject.toml` with `payments-py[fastapi]`, `fastapi`, `uvicorn`, `openai`
- Create a basic project structure
- Set up `.env` loading with `python-dotenv`

> "Notice Claude is consulting the Nevermined MCP server to get the exact package names and import paths. It's not guessing."

#### Phase 2: Core agent logic (7 min)

```
> Now create the main agent file. It should:
> 1. Initialize Nevermined Payments from environment variables
> 2. Add the x402 PaymentMiddleware to protect POST /ask (1 credit per request)
> 3. The /ask endpoint should take a JSON body with a "query" field
> 4. Use OpenAI to generate an answer about the query
> 5. Add a GET /health endpoint (unprotected)
> 6. Run on port 8000
```

**Expected output — something like:**

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

app.add_middleware(
    PaymentMiddleware,
    payments=payments,
    routes={"POST /ask": {"plan_id": os.getenv("NVM_PLAN_ID"), "credits": 1}},
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(request: Request):
    body = await request.json()
    query = body.get("query", "")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a technology trends analyst."},
            {"role": "user", "content": query},
        ],
    )
    return {"answer": response.choices[0].message.content}
```

> "In about 2 minutes, Claude built a fully working payment-protected agent. The middleware handles everything: when someone calls /ask without a payment token, they get a 402 response telling them how to pay. When they include a valid token, the request goes through and credits are settled."

#### Phase 3: Add more features (5 min)

Ask Claude to enhance the agent:

```
> Add a /pricing endpoint (GET, unprotected) that returns the plan ID, cost per
> query, and a human-readable description of what this agent does. Also add
> request logging so we can see payment verifications and settlements in the
> console.
```

> "This is the vibe coding flow — you describe what you want, Claude implements it. You don't need to look up API docs because Claude already has them via MCP."

#### Phase 4: Build a client (5 min)

```
> Now create a simple client script that:
> 1. Calls /ask without a token (should get 402)
> 2. Parses the 402 response to show payment requirements
> 3. Gets an x402 access token using the payments SDK
> 4. Retries the request with the token
> 5. Shows the response and credits used
```

**Expected output — demonstrates the full x402 flow:**

```python
import requests
from payments_py import Payments, PaymentOptions

payments = Payments.get_instance(PaymentOptions(
    nvm_api_key=os.getenv("NVM_API_KEY"),
    environment="sandbox",
))

# Step 1: Call without token
response = requests.post("http://localhost:8000/ask",
    json={"query": "What are the top AI trends in 2026?"})
print(f"Status: {response.status_code}")  # 402

# Step 2: Get payment token
token = payments.x402.get_x402_access_token(plan_id=NVM_PLAN_ID)

# Step 3: Retry with token
response = requests.post("http://localhost:8000/ask",
    json={"query": "What are the top AI trends in 2026?"},
    headers={"payment-signature": token})
print(f"Status: {response.status_code}")  # 200
print(f"Answer: {response.json()['answer']}")
```

> "That's the complete cycle. No payment? 402. Valid payment? 200 with answer. Credits settled automatically."

#### Phase 5: Install and test (5 min)

```bash
# Install dependencies
poetry install

# Start the agent (terminal 1)
poetry run uvicorn agent:app --host 0.0.0.0 --port 8000

# Run the client (terminal 2)
poetry run python client.py
```

Walk through the output:
1. Show the 402 response with `payment-required` header
2. Show the token generation
3. Show the successful 200 response
4. Show the settlement in the agent's console logs

---

### Section 6: Testing the Agent (10 min)

**[BOTH TERMINALS VISIBLE]**

> "Let's see this in action end to end."

**Demo flow:**

1. **Health check** (works without payment):
   ```bash
   curl http://localhost:8000/health
   ```

2. **Pricing check** (works without payment):
   ```bash
   curl http://localhost:8000/pricing
   ```

3. **Ask without payment** (gets 402):
   ```bash
   curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the future of autonomous agents?"}' \
     -v
   ```
   Point out the `payment-required` header in the 402 response.

4. **Run the client script** (full payment flow):
   ```bash
   poetry run python client.py
   ```
   Walk through each step as it executes.

5. **Check balance on nevermined.app:**
   Show the credits being consumed in the Nevermined dashboard.

> "In under 30 minutes, we went from an empty directory to a fully monetized AI agent. That's the power of vibe coding with Claude Code and the Nevermined MCP server."

**If time permits — bonus:**

```
> Add observability to the agent using payments.observability.with_openai()
> so we can track LLM costs per request in Nevermined's dashboard.
```

---

### Section 7: Q&A + Resources (5 min)

**[SLIDE 5: Resources]**

| Resource | URL |
|----------|-----|
| Nevermined Docs | https://docs.nevermined.app |
| Nevermined App | https://nevermined.app |
| AI Skill Install Guide | https://nevermined.ai/docs/development-guide/build-using-nvm-skill |
| MCP Server | https://docs.nevermined.app/mcp |
| LLM Context File | https://docs.nevermined.app/assets/nevermined_mcp_for_llms.txt |
| Payments Python SDK | https://github.com/nevermined-io/payments-py |
| Payments TypeScript SDK | https://github.com/nevermined-io/payments |
| Hackathon Starter Kits | This repo (`starter-kits/`) |
| Discord | https://discord.com/invite/GZju2qScKq |

**[SLIDE 6: Try it yourself]**

> "Now it's your turn. You have the MCP server, you have the starter kits. Pick a track, describe what you want to build, and let Claude Code + Nevermined do the heavy lifting. We're here to help."

**Encourage participants to:**
1. Install the AI Skill + connect the MCP server (takes 60 seconds)
2. Pick a starter kit README as inspiration
3. Start vibe coding their own agent — let Claude do the heavy lifting

---

## Troubleshooting Notes (for presenter)

| Issue | Fix |
|-------|-----|
| Skill not detected by Claude Code | Check `~/.claude/skills/nevermined-payments/skill.md` exists; restart Claude Code |
| MCP server won't connect | Check internet, try `curl https://docs.nevermined.app/mcp`; skill alone is sufficient |
| 402 response but can't get token | Check `NVM_API_KEY` is valid sandbox key |
| Token works but settlement fails | Check plan has credits available, subscriber ordered the plan |
| Claude doesn't use Nevermined APIs correctly | Check skill is installed; restart Claude Code to reload skill + MCP |
| Poetry install fails | Try `pip install payments-py[fastapi] fastapi uvicorn openai` instead |
| Port 8000 already in use | Use `--port 8001` or kill existing process |

---

## Backup Plan

If live coding fails (network issues, API errors), have these ready:
1. **Pre-built agent**: Clone `agents/seller-simple-agent/` and walk through the code
2. **Pre-recorded screencast**: 5-minute recording of the live coding session
3. **Code snippets**: The expected output from each phase above, ready to paste
