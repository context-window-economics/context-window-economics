# context-window-economics (TypeScript)

Bilateral cost allocation, context pricing, and resource markets for autonomous agent interactions. TypeScript reference implementation of the Context Window Economics Protocol (CWEP).

Part of the **AB Support Trust Ecosystem** — Layer 4 (Market/Economics).

## What It Does

CWEP tracks and allocates the real inference costs of agent-to-agent interactions across all four token flows:

- **Request Output (RO)** — requestor generates the request
- **Request Input (RI)** — responder processes the request (the "cost of understanding")
- **Response Output (SO)** — responder generates the response
- **Response Input (SI)** — requestor processes the response

## Install

```bash
npm install context-window-economics
```

Requires Node.js >= 18.0.0. Zero runtime dependencies.

## Quick Start

```typescript
import { Meter, allocate, SettlementEngine, SettlementTier } from "context-window-economics";

// Create a meter for your agent
const meter = new Meter({
  agentId: "did:web:my-agent",
  model: "claude-sonnet-4-6",
  provider: "anthropic",
});

// Record an interaction
const cmr = meter.recordInteraction({
  responderId: "did:web:other-agent",
  requestTokens: 10000,
  responseTokens: 3000,
});

console.log(`Total cost: $${cmr.totals.totalCostUsd.toFixed(4)}`);
console.log(`Requestor incurred: $${cmr.totals.requestorIncurredUsd.toFixed(4)}`);
console.log(`Responder incurred: $${cmr.totals.responderIncurredUsd.toFixed(4)}`);

// Compute fair cost allocation (Shapley value)
const proposal = allocate(cmr, "shapley");
console.log(`Requestor should pay: $${proposal.requestorPaysUsd.toFixed(4)}`);
console.log(`Responder should pay: $${proposal.responderPaysUsd.toFixed(4)}`);
```

## Modules

| Module | Description |
|--------|-------------|
| `types` | Enums, constants, data structures (CMR, AgentPricing, TokenFlow, etc.) |
| `metering` | Token meter, flow cost computation, cost estimation |
| `allocation` | Cost allocation: requestor-pays, responder-pays, equal split, proportional, Shapley, Nash |
| `settlement` | Settlement engine, batching, CMR hashing, payment rail abstraction |
| `spam` | Deposit calculation, reputation-based access, progressive request limits |
| `congestion` | Congestion pricing, QoS tiers, back-pressure signals, position-dependent pricing |
| `caching` | Cache amortization, compression ROI, memory vs. context crossover analysis |
| `store` | Append-only JSONL persistence for CMRs, settlements, and deposits |

## Allocation Methods

- **Requestor pays** — status quo: requestor bears 100% of cost
- **Responder pays** — responder bears 100%
- **Equal split** — 50/50
- **Proportional** — split by token share
- **Shapley value** — fair division based on marginal contribution (recommended)
- **Nash bargaining** — bilateral negotiation with configurable bargaining power

## Build

```bash
npm install
npm run build
npm test
```

## Configuration

Provider pricing defaults are included for Anthropic, OpenAI, and Google models as of March 2026. Custom pricing:

```typescript
import { AgentPricing, Meter } from "context-window-economics";

const customPricing = new AgentPricing({
  inputRatePerMtok: 2.0,
  outputRatePerMtok: 10.0,
  cacheHitRatePerMtok: 0.2,
});

const meter = new Meter({
  agentId: "my-agent",
  pricing: customPricing,
});
```

## Trust Ecosystem Integration

CWEP integrates with:
- **Chain of Consciousness** — `cocChainRef` field links CMRs to CoC entries
- **Agent Rating Protocol** — reputation scores drive deposit multipliers and access tiers
- **Agent Service Agreements** — cost terms embedded in contracts reference CWEP allocation methods

## License

Apache-2.0
