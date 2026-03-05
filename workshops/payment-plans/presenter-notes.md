# Workshop: Payment Plans, Credits & Dynamic Pricing

**Duration:** 45-60 minutes
**Goal:** Participants understand the different pricing models, register an agent with a payment plan, experience the subscriber flow, and implement dynamic pricing based on request complexity.

---

## Format Recommendation

| Element | Recommendation |
|---------|----------------|
| **Slides** | Use the Keynote in this folder (`Payment plans.key`) |
| **Live demo** | Code-along for each pricing pattern |
| **Browser** | nevermined.app to create plans and show balances |
| **Terminal** | Two terminals: server + client |

**Why this order:** Start with plan types (conceptual), then registration (builder side), then subscriber flow (consumer side), then dynamic pricing (advanced). Each file builds on the previous.

---

## Pre-Workshop Checklist

### Your machine (presenter)

- [ ] `payments-py` installed (`pip install payments-py`)
- [ ] Valid `NVM_API_KEY` (sandbox builder key)
- [ ] A second `NVM_API_KEY` for subscriber testing (different account)
- [ ] `.env` configured with all variables
- [ ] Workshop files tested end-to-end
- [ ] nevermined.app open in browser to show plans and balances
- [ ] Terminal font size large enough for projection

### Participant machines

- [ ] Python 3.10+ or Node.js 18+
- [ ] Nevermined sandbox account + API key
- [ ] Ideally two accounts (builder + subscriber) — or pair up

---

## Agenda

| Time | Section | Format | Files |
|------|---------|--------|-------|
| 0:00 - 0:05 | Why credits? The pricing abstraction | Slides | — |
| 0:05 - 0:15 | Plan types: fixed, dynamic, time, PAYG, trial | Live code | `plan_types.py` / `plan-types.ts` |
| 0:15 - 0:25 | Registering an agent + plan | Live code | `register_agent.py` / `register_agent_fiat.py` / `register-agent.ts` |
| 0:25 - 0:35 | The subscriber experience | Live code | `subscriber.py` / `subscriber.ts` |
| 0:35 - 0:50 | Dynamic pricing server | Live code | `dynamic_pricing.py` / `dynamic-pricing.ts` |
| 0:50 - 1:00 | Q&A | Open | — |

---

## Detailed Script

### Section 1: Why Credits? (5 min)

**Key talking points:**

> "Credits are an abstraction between your pricing and your cost. You can change prices without changing code — charge 100 credits for $10 or 500 for $40. Bulk discounts, free trials, different currencies — all without touching your middleware."

- Credits work identically for crypto (USDC) and fiat (Stripe)
- Settlement on Base L2: ~$0.0001 per transaction — micropayments are viable
- Credits are ERC-1155 tokens on-chain — fully auditable

---

### Section 2: Plan Types (10 min)

**Open `python/plan_types.py`**

Walk through each plan type:

1. **Fixed Credits** — `get_fixed_credits_config(100, 1)` — 100 credits, 1 per request
   > "Simple and predictable. Most common for getting started."

2. **Dynamic Credits** — `get_dynamic_credits_config(100, 1, 10)` — 1 to 10 credits per request
   > "The middleware decides the cost at runtime. We'll build this in section 5."

3. **Time-Based** — `get_expirable_duration_config(2_592_000)` — 30 days unlimited
   > "Subscription model. No credit counting."

4. **Pay-As-You-Go** — `get_pay_as_you_go_credits_config()` — settle in USDC per request
   > "No prepurchase. Great for enterprise or high-value, infrequent calls."

5. **Free Trial** — Fixed credits with price = 0
   > "Onboarding tool. Give 10 free credits to try your agent."

**Then show price configurations (positional args only):**

- **Crypto**: `get_crypto_price_config(10_000_000, builder_address, USDC_ADDRESS)` — $10 USDC (6 decimals)
- **Fiat**: `get_fiat_price_config(1000, builder_address)` — $10.00 in cents via Stripe

> "Your middleware code is identical for both. The SDK auto-detects the scheme from plan metadata."

**Show TypeScript equivalent (`ts/plan-types.ts`):**

> "Same patterns, but TypeScript uses BigInt for amounts: `100n` instead of `100`, `10_000_000n` for crypto prices."

---

### Section 3: Registering an Agent + Plan (10 min)

**Open `python/register_agent.py`**

> "One call to register both your agent and its payment plan."


```python
from payments_py.plans import get_erc20_price_config, get_fixed_credits_config

USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
builder_address = payments.account_address

result = payments.agents.register_agent_and_plan(
    agent_metadata={
        "name": "My AI Agent",
        "description": "AI analysis service",
        "tags": ["ai", "analysis"],
    },
    agent_api={
        "endpoints": [{"POST": "https://your-server.com/ask"}],
        "agentDefinitionUrl": "https://your-server.com/openapi.json",
    },
    plan_metadata={
        "name": "Pro Plan",
        "description": "100 credits for 10 USDC",
    },
    price_config=get_erc20_price_config(10_000_000, USDC_ADDRESS, builder_address),
    credits_config=get_fixed_credits_config(100, 1),
    access_limit="credits",
)
print(f"Agent ID: {result['agentId']}")  # did:nv:...
print(f"Plan ID:  {result['planId']}")   # did:nv:...
```

**Key talking points:**
- **`agentDefinitionUrl` is required** in `agent_api` — point it at your OpenAPI spec or agent card
- **ERC20 pricing** — Default example uses USDC on Base Sepolia; the price helper is `get_erc20_price_config`
- Save `agentId` and `planId` to your `.env` — you'll need them for everything
- You can also do this no-code via nevermined.app (show it in browser)
- One agent can have multiple plans (e.g., free trial + pro plan)

**Fiat alternative: show `python/register_agent_fiat.py`**

> "If you want to accept credit cards via Stripe instead of crypto, use `get_fiat_price_config`. The rest of the code is identical — just swap the price config."

- Requires Stripe Connect setup in nevermined.app first (Settings > Payments > Connect Stripe)
- Uses `get_fiat_price_config(999, builder_address)` — price in cents ($9.99)
- Good to mention but don't code-along unless audience specifically needs fiat

**Alternative: show nevermined.app UI**
- Navigate to My Agents > New Agent
- Fill in metadata, create plan, copy IDs
- Useful for non-technical team members

---

### Section 4: The Subscriber Experience (10 min)

**Open `python/subscriber.py`**

> "Now let's flip to the buyer side. This uses a SUBSCRIBER API key — different from the builder key."

Walk through the 4 steps:

1. **Check balance**: `payments.plans.get_plan_balance(PLAN_ID)`
2. **Buy plan if needed**: `payments.plans.order_plan(PLAN_ID)`
3. **Get token**: `token_result = payments.x402.get_x402_access_token(PLAN_ID)` → `token_result["accessToken"]`
4. **Use the token**: `headers={"payment-signature": access_token}`

**Run it against the server from Workshop 1:**
```bash
# Terminal 1 (from getting-started workshop)
python server.py

# Terminal 2
python subscriber.py
```

> "The subscriber doesn't need to know how much things cost in advance. They can discover pricing from the 402 response — auto-discovery pattern."

---

### Section 5: Dynamic Pricing (15 min)

**Open `python/dynamic_pricing.py`**

> "This is where it gets interesting. Instead of a fixed number, pass a function."

```python
"credits": lambda req: max(1, len(req.body.get("prompt", "")) // 500),
```

> "Short prompt? 1 credit. Long prompt? More credits. The function receives the request object and decides at settlement time."

**Show the TypeScript version (`ts/dynamic-pricing.ts`):**
```typescript
credits: (req: any) => {
    const prompt = req.body?.prompt || "";
    return Math.max(1, Math.ceil(prompt.length / 500));
}
```

**Live demo:**
```bash
# Start dynamic pricing server
python dynamic_pricing.py

# Short prompt (1 credit)
curl -X POST http://localhost:3000/generate \
  -H "payment-signature: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'

# Long prompt (more credits)
curl -X POST http://localhost:3000/generate \
  -H "payment-signature: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a very long essay about..."}'
```

> "Check the `credits_charged` in the response — different amounts for different requests."

**Important constraint:**
> "The amount must stay within the plan's min/max credits range — that's what `get_dynamic_credits_config(100, 1, 10)` sets."

---

## Troubleshooting Notes (for presenter)

| Issue | Fix |
|-------|-----|
| `register_agent_and_plan` fails | Check API key has builder permissions; check account is verified; ensure dicts use camelCase keys |
| Pydantic serialization errors | Don't use `AgentMetadata(...)` etc. — use plain dicts with camelCase keys instead |
| Missing `agentDefinitionUrl` | This field is required in `agent_api` — add a URL to your OpenAPI spec or agent card |
| `order_plan` fails | Subscriber needs sufficient balance (sandbox plans can be free) |
| Dynamic pricing charges wrong amount | Lambda receives the raw request — check `req.body` structure |
| "Plan not found" | Check `NVM_PLAN_ID` matches a real plan; check environment matches |
| TypeScript BigInt errors | Ensure values use `n` suffix: `100n`, not `100` |

---

## Backup Plan

If registration fails or API is slow:
1. **Use pre-created plan IDs** — have agent + plan IDs ready in your `.env`
2. **Skip to subscriber.py** — the subscriber flow works with any existing plan
3. **Focus on dynamic_pricing.py** — this is the most engaging demo
