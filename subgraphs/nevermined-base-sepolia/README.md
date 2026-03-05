# Nevermined Subgraph — Base Sepolia

A [The Graph](https://thegraph.com/) subgraph that indexes all Nevermined protocol activity on Base Sepolia. Deployed on [Goldsky](https://goldsky.com/) for free testnet indexing.

## GraphQL Endpoint

```
https://api.goldsky.com/api/public/project_cmmdxa29pqd7301x809tn06ng/subgraphs/nevermined-base-sepolia/1.0.0/gn
```

No authentication required. Open the URL in a browser for an interactive GraphQL playground.

## What It Indexes

| Data Source | Contract | What It Tracks |
|-------------|----------|----------------|
| **NFT1155Credits** | `0xb2F9bB43F768E0D4ADCa49CE708acbE577bC2d64` | Credit mints, burns (redemptions), transfers |
| **NFT1155ExpirableCreditsV2** | `0xF7Fe16718a779010E48859fb1c7Eae9fd540872F` | Same events for expirable credits |
| **AgreementsStore** | `0x1B8B04BbF240bfB15f12368352a1397E3882660C` | Agreement creation, condition fulfillment |
| **USDC** | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | Payments to PaymentsVault |

### On-Chain Event Flow

When a user purchases credits (crypto or Stripe/fiat):

1. **AgreementRegistered** — a new agreement is created in `AgreementsStore`
2. **ConditionUpdated** (x2) — payment settlement + credit transfer conditions are fulfilled
3. **TransferSingle** (mint) — credits are minted to the buyer (from = `0x0`)

When credits are redeemed (used to call an AI agent):

4. **TransferSingle/TransferBatch** (burn) — credits are burned (to = `0x0`)

When paying with USDC:

5. **ERC20 Transfer** — USDC moves from buyer to `PaymentsVault` (`0x47A72d7094c4c5B0566E159579DBD79220A0EA24`)

## Entities

| Entity | Description |
|--------|-------------|
| `CreditTransfer` | Every credit mint, burn, or transfer event |
| `DailyPlanStats` | Aggregated daily stats per plan (mints, burns, amounts) |
| `USDCPayment` | USDC transfers to the PaymentsVault |
| `Agreement` | Registered agreements (purchases) |
| `ConditionUpdate` | Condition state changes within agreements |
| `ProtocolStats` | Global cumulative protocol metrics |

## Schema Reference

### CreditTransfer

Emitted every time credits are minted, burned, or transferred between wallets. This is the core entity for tracking credit activity.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Bytes!` | Unique ID derived from transaction hash + log index |
| `type` | `String!` | `"mint"` (from = zero address), `"burn"` (to = zero address), or `"transfer"` (wallet to wallet) |
| `operator` | `Bytes!` | Address that initiated the transaction (may differ from `from` when using account abstraction / session keys) |
| `from` | `Bytes!` | Sender address. `0x000...000` for mints |
| `to` | `Bytes!` | Receiver address. `0x000...000` for burns |
| `planId` | `BigInt!` | The Nevermined plan ID (ERC1155 token ID). Identifies which AI agent/service plan the credits belong to |
| `amount` | `BigInt!` | Number of credits minted, burned, or transferred |
| `blockNumber` | `BigInt!` | Block number on Base Sepolia |
| `blockTimestamp` | `BigInt!` | Unix timestamp of the block |
| `transactionHash` | `Bytes!` | Transaction hash on Base Sepolia |

### DailyPlanStats

Pre-aggregated daily statistics per plan. Useful for building time-series charts without client-side aggregation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `String!` | Composite key: `"YYYY-MM-DD-{planId}"` |
| `date` | `String!` | Date string in `YYYY-MM-DD` format |
| `planId` | `BigInt!` | The Nevermined plan ID |
| `mintCount` | `Int!` | Number of mint transactions that day |
| `burnCount` | `Int!` | Number of burn (redemption) transactions that day |
| `transferCount` | `Int!` | Number of wallet-to-wallet transfers that day |
| `creditsMinted` | `BigInt!` | Total credits minted that day for this plan |
| `creditsBurned` | `BigInt!` | Total credits burned (redeemed) that day for this plan |
| `creditsTransferred` | `BigInt!` | Total credits transferred between wallets that day |

### USDCPayment

Tracks USDC (ERC20) transfers sent to the Nevermined `PaymentsVault` contract. Only transfers **to** the vault are indexed — other USDC activity is ignored.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Bytes!` | Unique ID derived from transaction hash + log index |
| `from` | `Bytes!` | Payer wallet address |
| `amount` | `BigDecimal!` | USDC amount in human-readable form (divided by 10^6) |
| `rawAmount` | `BigInt!` | Raw USDC amount in smallest unit (6 decimals). `1000000` = 1 USDC |
| `blockNumber` | `BigInt!` | Block number on Base Sepolia |
| `blockTimestamp` | `BigInt!` | Unix timestamp of the block |
| `transactionHash` | `Bytes!` | Transaction hash on Base Sepolia |

### Agreement

Created when a user purchases a plan (crypto or fiat/Stripe). Each agreement contains conditions that must be fulfilled to complete the purchase and deliver credits.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Bytes!` | The `agreementId` (bytes32 hash) — unique identifier for this purchase agreement |
| `creator` | `Bytes!` | Address that created the agreement (usually the buyer or the Nevermined node on behalf of the buyer) |
| `conditions` | `[ConditionUpdate!]!` | Derived relation — all condition state changes for this agreement |
| `blockNumber` | `BigInt!` | Block number on Base Sepolia |
| `blockTimestamp` | `BigInt!` | Unix timestamp of the block |
| `transactionHash` | `Bytes!` | Transaction hash on Base Sepolia |

### ConditionUpdate

Tracks condition state changes within an agreement. A typical purchase has 2 conditions: a payment/settlement condition and a credit transfer condition. Both must be fulfilled for the purchase to complete.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `Bytes!` | Unique ID derived from transaction hash + log index |
| `agreement` | `Agreement!` | Reference to the parent agreement |
| `conditionId` | `Bytes!` | The condition's unique identifier (bytes32 hash) |
| `state` | `Int!` | Condition state: `0` = Uninitialized, `1` = Unfulfilled, `2` = Fulfilled, `3` = Aborted |
| `blockNumber` | `BigInt!` | Block number on Base Sepolia |
| `blockTimestamp` | `BigInt!` | Unix timestamp of the block |
| `transactionHash` | `Bytes!` | Transaction hash on Base Sepolia |

### ProtocolStats

A single global entity (`id: "global"`) with cumulative protocol-wide metrics. Updated on every relevant event.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `String!` | Always `"global"` — there is only one instance |
| `totalMints` | `Int!` | Total number of credit mint events |
| `totalBurns` | `Int!` | Total number of credit burn (redemption) events |
| `totalCreditsMinted` | `BigInt!` | Cumulative credits minted across all plans |
| `totalCreditsBurned` | `BigInt!` | Cumulative credits burned across all plans |
| `totalUSDCVolume` | `BigDecimal!` | Cumulative USDC paid to the PaymentsVault (human-readable, e.g. `"1.50"`) |
| `totalAgreements` | `Int!` | Total number of agreements registered |
| `totalFulfilledConditions` | `Int!` | Total number of conditions that reached `Fulfilled` state |

## Query Examples

### Global Protocol Stats

Get a high-level overview of all Nevermined activity:

```graphql
{
  protocolStats(id: "global") {
    totalMints
    totalBurns
    totalCreditsMinted
    totalCreditsBurned
    totalUSDCVolume
    totalAgreements
    totalFulfilledConditions
  }
}
```

### Credit Mints (Purchases)

All credit purchases, most recent first:

```graphql
{
  creditTransfers(
    where: { type: "mint" }
    orderBy: blockTimestamp
    orderDirection: desc
    first: 20
  ) {
    to
    planId
    amount
    blockTimestamp
    transactionHash
  }
}
```

### Credit Burns (Redemptions)

All credit redemptions when agents are called:

```graphql
{
  creditTransfers(
    where: { type: "burn" }
    orderBy: blockTimestamp
    orderDirection: desc
    first: 20
  ) {
    from
    planId
    amount
    blockTimestamp
    transactionHash
  }
}
```

### Credit Transfers Between Users

Credits transferred between wallets (not mints or burns):

```graphql
{
  creditTransfers(
    where: { type: "transfer" }
    orderBy: blockTimestamp
    orderDirection: desc
    first: 20
  ) {
    from
    to
    planId
    amount
    blockTimestamp
    transactionHash
  }
}
```

### USDC Payments

All USDC payments to the Nevermined PaymentsVault:

```graphql
{
  usdcpayments(
    orderBy: blockTimestamp
    orderDirection: desc
    first: 20
  ) {
    from
    amount
    rawAmount
    blockTimestamp
    transactionHash
  }
}
```

### Large USDC Payments (Above a Threshold)

Filter payments above 1 USDC:

```graphql
{
  usdcpayments(
    where: { rawAmount_gt: "1000000" }
    orderBy: amount
    orderDirection: desc
  ) {
    from
    amount
    blockTimestamp
    transactionHash
  }
}
```

### Daily Stats Per Plan

Aggregated daily activity broken down by plan:

```graphql
{
  dailyPlanStats(
    orderBy: date
    orderDirection: desc
    first: 30
  ) {
    date
    planId
    mintCount
    burnCount
    transferCount
    creditsMinted
    creditsBurned
    creditsTransferred
  }
}
```

### Daily Stats for a Specific Plan

Filter to a single plan ID:

```graphql
{
  dailyPlanStats(
    where: { planId: "12345" }
    orderBy: date
    orderDirection: desc
    first: 30
  ) {
    date
    mintCount
    burnCount
    creditsMinted
    creditsBurned
  }
}
```

### Agreements (Purchases)

Recent agreements with their condition states:

```graphql
{
  agreements(
    orderBy: blockTimestamp
    orderDirection: desc
    first: 10
  ) {
    id
    creator
    blockTimestamp
    transactionHash
    conditions {
      conditionId
      state
      blockTimestamp
    }
  }
}
```

Condition states: `0` = Uninitialized, `1` = Unfulfilled, `2` = Fulfilled, `3` = Aborted.

### Agreements by Creator

Filter agreements by a specific wallet:

```graphql
{
  agreements(
    where: { creator: "0xfb340ff496d1c34a1a5d45a97821d6a704696755" }
    orderBy: blockTimestamp
    orderDirection: desc
  ) {
    id
    blockTimestamp
    transactionHash
    conditions {
      state
    }
  }
}
```

### Fulfilled Conditions Only

Find all successfully completed conditions:

```graphql
{
  conditionUpdates(
    where: { state: 2 }
    orderBy: blockTimestamp
    orderDirection: desc
    first: 20
  ) {
    agreement {
      id
      creator
    }
    conditionId
    blockTimestamp
    transactionHash
  }
}
```

### All Activity for a Specific Address

Combine credit burns and mints for a wallet:

```graphql
{
  burns: creditTransfers(
    where: { from: "0xfb340ff496d1c34a1a5d45a97821d6a704696755", type: "burn" }
    orderBy: blockTimestamp
    orderDirection: desc
  ) {
    planId
    amount
    blockTimestamp
  }
  mints: creditTransfers(
    where: { to: "0xfb340ff496d1c34a1a5d45a97821d6a704696755", type: "mint" }
    orderBy: blockTimestamp
    orderDirection: desc
  ) {
    planId
    amount
    blockTimestamp
  }
  payments: usdcpayments(
    where: { from: "0xfb340ff496d1c34a1a5d45a97821d6a704696755" }
    orderBy: blockTimestamp
    orderDirection: desc
  ) {
    amount
    blockTimestamp
  }
}
```

### Pagination

Use `skip` and `first` for paginated results:

```graphql
{
  creditTransfers(
    orderBy: blockTimestamp
    orderDirection: desc
    first: 10
    skip: 20
  ) {
    type
    planId
    amount
    blockTimestamp
  }
}
```

### Time Range Filter

Filter events within a time window (Unix timestamps):

```graphql
{
  creditTransfers(
    where: {
      blockTimestamp_gte: "1763100000"
      blockTimestamp_lte: "1763200000"
    }
    orderBy: blockTimestamp
    orderDirection: desc
  ) {
    type
    from
    to
    planId
    amount
    blockTimestamp
  }
}
```

### Count Events by Type

Get totals for mints vs burns:

```graphql
{
  mints: creditTransfers(where: { type: "mint" }) { id }
  burns: creditTransfers(where: { type: "burn" }) { id }
  transfers: creditTransfers(where: { type: "transfer" }) { id }
}
```

> Note: The Graph limits results to 1000 per query. For exact counts, use `protocolStats`.

## Querying from Code

### curl

```bash
curl -s -X POST \
  'https://api.goldsky.com/api/public/project_cmmdxa29pqd7301x809tn06ng/subgraphs/nevermined-base-sepolia/1.0.0/gn' \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ protocolStats(id:\"global\") { totalMints totalBurns totalUSDCVolume } }"}'
```

### TypeScript / JavaScript

```typescript
const SUBGRAPH_URL =
  'https://api.goldsky.com/api/public/project_cmmdxa29pqd7301x809tn06ng/subgraphs/nevermined-base-sepolia/1.0.0/gn'

async function query(graphql: string) {
  const res = await fetch(SUBGRAPH_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: graphql }),
  })
  const { data } = await res.json()
  return data
}

// Example: get recent burns
const data = await query(`{
  creditTransfers(where: { type: "burn" }, orderBy: blockTimestamp, orderDirection: desc, first: 10) {
    planId
    amount
    from
    blockTimestamp
  }
}`)
```

### Python

```python
import requests

SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cmmdxa29pqd7301x809tn06ng/subgraphs/nevermined-base-sepolia/1.0.0/gn"

def query(graphql: str):
    response = requests.post(SUBGRAPH_URL, json={"query": graphql})
    return response.json()["data"]

# Example: get protocol stats
data = query('{ protocolStats(id: "global") { totalMints totalBurns totalUSDCVolume } }')
print(data)
```

## Development

### Prerequisites

- Node.js 18+
- npm

### Setup

```bash
cd subgraphs/nevermined-base-sepolia
npm install
```

### Build

```bash
npm run codegen    # Generate types from schema + ABIs
npm run build      # Compile to WASM
```

### Deploy to Goldsky

[Goldsky](https://goldsky.com/) is the recommended deployment target because it supports Base Sepolia (The Graph's decentralized network only supports mainnets).

#### 1. Create a Goldsky Account

Sign up at https://app.goldsky.com (free tier includes 500K rows).

#### 2. Install the Goldsky CLI

```bash
curl https://goldsky.com | sh
```

Or download directly:
```bash
curl -fsSL https://cli.goldsky.com/latest/linux/goldsky -o /usr/local/bin/goldsky
chmod +x /usr/local/bin/goldsky
```

#### 3. Authenticate

Get your API key from https://app.goldsky.com/dashboard/settings, then:

```bash
goldsky login
# Paste your API key when prompted
```

Or non-interactively:
```bash
goldsky login --token YOUR_API_KEY
```

#### 4. Build and Deploy

```bash
cd subgraphs/nevermined-base-sepolia
npm install
npm run codegen
npm run build
npm run deploy:goldsky
```

This deploys as `nevermined-base-sepolia/1.0.0`. The version is set in `package.json` under the `deploy:goldsky` script.

#### 5. Verify Deployment

```bash
goldsky subgraph list
```

You should see:
```
* nevermined-base-sepolia/1.0.0
    Status: healthy (Active)
    Chain: base-sepolia
```

#### 6. Monitor Sync Progress

```bash
goldsky subgraph list
```

The `Synced` percentage shows how far the indexer has caught up to the chain head. The subgraph starts indexing from block `33681969` (contract deployment block), not from genesis.

#### Updating the Subgraph

To deploy a new version after making changes:

```bash
npm run codegen
npm run build
goldsky subgraph deploy nevermined-base-sepolia/1.1.0 --path .
```

#### Deleting a Deployment

```bash
goldsky subgraph delete nevermined-base-sepolia/1.0.0
```

### Deploy to a Self-Hosted Graph Node

If you prefer running your own infrastructure:

```bash
# Requires a running Graph Node connected to a Base Sepolia RPC
npm run deploy:local
```

## Contract Addresses (Base Sepolia v1.3.2)

| Contract | Address |
|----------|---------|
| NFT1155Credits | `0xb2F9bB43F768E0D4ADCa49CE708acbE577bC2d64` |
| NFT1155ExpirableCredits | `0x6de675a697f9131D061F265fAf88E26158f4FfA2` |
| NFT1155ExpirableCreditsV2 | `0xF7Fe16718a779010E48859fb1c7Eae9fd540872F` |
| AgreementsStore | `0x1B8B04BbF240bfB15f12368352a1397E3882660C` |
| PaymentsVault | `0x47A72d7094c4c5B0566E159579DBD79220A0EA24` |
| USDC | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| FiatPaymentTemplate | `0x386eF80de6Afe51838672Ec6c08081C3f6A2C2d8` |
| FixedPaymentTemplate | `0x32037D176558Eb02f6980eFA14bde14B0C61d059` |
| PayAsYouGoTemplate | `0x5e852077b30099106Aa65B4d329FFF9b5C9a8e7C` |
