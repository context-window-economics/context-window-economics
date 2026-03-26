# Context Window Economics Protocol (CWEP)

Bilateral cost allocation, context pricing, and resource markets for autonomous agent interactions.

When Agent A sends Agent B a request, Agent B pays real dollars to *read* it. CWEP makes this invisible cost visible, allocable, and settleable.

## Install

```bash
pip install context-window-economics
```

Optional integrations:

```bash
pip install context-window-economics[arp]    # Agent Rating Protocol
pip install context-window-economics[trust]  # Full trust ecosystem
pip install context-window-economics[dev]    # pytest
```

## What It Does

1. **Token Metering** -- tracks all four cost flows in every agent interaction (request output, request input, response output, response input)
2. **Cost Allocation** -- three methods: rule-based (requestor-pays, split, proportional), Shapley value (fair division), Nash bargaining (bilateral negotiation)
3. **Settlement** -- generates settlement proposals, batches transactions, abstracts payment rails (x402, MPP, L402, Superfluid)
4. **Spam Prevention** -- deposit-based filtering with reputation-weighted access tiers
5. **Congestion Pricing** -- utilization-based multipliers, QoS tiers (economy/standard/priority/reserved), back-pressure signaling
6. **Caching Economics** -- cost amortization, compression ROI, memory vs. long-context crossover analysis

## CLI Quick Start

```bash
# Estimate interaction cost
cwep estimate --request-tokens 10000 --response-tokens 3000

# Record an interaction
cwep meter --requestor agent-a --responder agent-b \
    --request-tokens 10000 --response-tokens 3000

# Compute cost allocation
cwep allocate --requestor agent-a --responder agent-b \
    --request-tokens 10000 --response-tokens 3000 --method shapley

# Generate settlements from recorded interactions
cwep settle --method shapley

# View cost summary
cwep status

# JSON output for scripting
cwep --json estimate --request-tokens 50000 --response-tokens 10000
```

## Python API

### Token Metering

```python
from context_window_economics import Meter

meter = Meter(agent_id="did:example:my-agent",
              model="claude-sonnet-4-6", provider="anthropic")

cmr = meter.record_interaction(
    responder_id="did:example:other-agent",
    responder_model="claude-opus-4-6",
    responder_provider="anthropic",
    request_tokens=10000,
    response_tokens=3000,
)

print(f"Total cost: ${cmr.totals.total_cost_usd:.4f}")
print(f"Requestor incurred: ${cmr.totals.requestor_incurred_usd:.4f}")
print(f"Responder incurred: ${cmr.totals.responder_incurred_usd:.4f}")
```

### Cost Allocation

```python
from context_window_economics import allocate, allocate_shapley

# Shapley value (default) -- from cooperative game theory
proposal = allocate(cmr, method="shapley")
print(f"Requestor pays: ${proposal.requestor_pays_usd:.4f}")
print(f"Responder pays: ${proposal.responder_pays_usd:.4f}")

# Nash bargaining -- for competitive interactions
proposal = allocate(cmr, method="nash_bargaining",
                    value_a=1.0, value_b=0.5, alpha=0.6)

# Rule-based -- for static agreements
proposal = allocate(cmr, method="requestor_pays")
proposal = allocate(cmr, method="equal_split")
proposal = allocate(cmr, method="proportional")
```

### Settlement Engine

```python
from context_window_economics import SettlementEngine

engine = SettlementEngine(
    tier="tier_3_dynamic",
    method="shapley",
    threshold_usd=0.01,
)

proposal = engine.propose(cmr)
if proposal:
    receipt = engine.settle(cmr, proposal)
    print(f"Settled: ${receipt.amount_usd:.4f} {proposal.transfer_direction}")
```

### Settlement Batching

```python
from context_window_economics import SettlementBatch

batch = SettlementBatch(window_seconds=3600, threshold_usd=1.00)
for cmr in interaction_cmrs:
    batch.add(cmr)
    if batch.should_flush():
        result = batch.flush()
        print(f"Net settlement: ${result['net_amount_usd']:.4f}")
```

### Spam Prevention

```python
from context_window_economics import (
    calculate_deposit, check_access, create_deposit, resolve_deposit
)

# Check if a request should be allowed
allowed, reason = check_access(
    reputation_score=45.0,
    interaction_count=12,
    request_tokens=50000,
)

# Calculate required deposit
amount, tier = calculate_deposit(
    estimated_request_tokens=50000,
    responder_input_rate_per_mtok=5.0,  # Opus
    reputation_score=45.0,
)

# Create and resolve deposits
deposit = create_deposit("req-1", "resp-1", 50000, 5.0, reputation_score=45.0)
deposit = resolve_deposit(deposit, is_spam=False)  # Refunded
```

### Congestion Pricing

```python
from context_window_economics import (
    effective_token_price, congestion_multiplier, generate_back_pressure
)

# Three-component pricing: base + congestion + overhead
price = effective_token_price(
    base_rate_per_mtok=3.0,
    tokens=100000,
    utilization=0.90,
    qos_tier="priority",
)
print(f"Effective price: ${price['total']:.4f}")
print(f"Congestion multiplier: {price['congestion_multiplier']:.2f}x")

# Back-pressure signaling
signal = generate_back_pressure(utilization=0.87, queue_depth=5)
print(f"Status: {signal.cwep_status}")
print(f"Available tiers: {signal.available_tiers}")
```

### Caching Economics

```python
from context_window_economics import (
    cache_amortized_cost, compression_roi, memory_vs_context_crossover
)

# Cache amortization across repeated interactions
result = cache_amortized_cost(
    context_tokens=100000,
    input_rate_per_mtok=3.0,
    num_interactions=10,
)
print(f"Amortized cost: ${result['amortized_cost']:.4f} ({result['savings_pct']:.0f}% savings)")

# Compression ROI
roi = compression_roi(
    uncompressed_tokens=50000,
    compressed_tokens=5000,
    input_rate_per_mtok=3.0,
)
print(f"Compression ROI: {roi['roi']:.1f}x")

# Memory vs. long-context decision
analysis = memory_vs_context_crossover(context_tokens=100000, input_rate_per_mtok=3.0)
print(f"Crossover at {analysis['crossover_point']} interactions")
print(f"Recommendation: {analysis['recommendation']}")
```

### Persistent Store

```python
from context_window_economics import CWEPStore

store = CWEPStore(".cwep")
store.append_cmr(cmr)

stats = store.statistics()
print(f"Total interactions: {stats['cmr_count']}")
print(f"Total cost: ${stats['total_cost_usd']:.2f}")
print(f"Per-agent costs: {stats['agent_costs']}")
```

## Architecture

```
context_window_economics/
  schema.py      -- Data structures, constants, enums (CMR, pricing, QoS)
  metering.py    -- Token metering, four cost flows, CMR generation
  allocation.py  -- Shapley, Nash, rule-based cost allocation
  settlement.py  -- Settlement engine, batching, payment rail abstraction
  spam.py        -- Deposits, reputation-weighted access, progressive sizing
  congestion.py  -- Congestion pricing, QoS tiers, back-pressure
  caching.py     -- Cache economics, compression ROI, memory analysis
  store.py       -- Append-only JSONL persistence
  cli.py         -- CLI entry point (cwep command)
```

## Trust Ecosystem Position

CWEP sits at **Layer 4 (Market/Economics)** of the AB Support Trust Ecosystem:

| Layer | Protocol | Function |
|-------|----------|----------|
| 5 | Agent Matchmaking Protocol | Discovery and matching |
| **4** | **Context Window Economics** | **Cost allocation and pricing** |
| 3 | Agent Service Agreements | Contract terms |
| 2 | Agent Rating Protocol | Reputation and trust scores |
| 1 | Chain of Consciousness | Provenance and auditability |

Cross-protocol integrations:
- **ARP**: Reputation scores inform bargaining power and deposit requirements
- **CoC**: CMR hashes anchored for auditability
- **ASA**: Cost allocation rules embedded in service agreements
- **AJP**: Cost disputes escalated through justice protocol
- **AMP**: Cost estimates provided for matchmaking

## The Four Cost Flows

Every agent interaction generates four distinct cost flows:

| Flow | Code | Who Pays | Description |
|------|------|----------|-------------|
| Request Output (RO) | `request_output` | Requestor | Generating the request |
| Request Input (RI) | `request_input` | Responder | Processing the request |
| Response Output (SO) | `response_output` | Responder | Generating the response |
| Response Input (SI) | `response_input` | Requestor | Processing the response |

Current payment protocols only price RO. CWEP prices all four.

## VAM-SEC Security Disclaimer

This package implements protocol-level economic logic for agent interactions. It does NOT:
- Handle real money transfers (use x402, MPP, L402, or Superfluid for actual payments)
- Provide cryptographic security for deposit escrow
- Replace proper authentication or authorization

For production deployments:
- Integrate with a real payment rail via the `PaymentRail` interface
- Validate CMRs against provider API responses
- Use CoC chain anchoring for audit trails
- Deploy behind proper API authentication

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Links

- [Whitepaper](https://vibeagentmaking.com/whitepaper/context-window-economics/)
- [GitHub](https://github.com/brycebostick/context-window-economics)
- [Trust Ecosystem](https://vibeagentmaking.com)

## License

Apache 2.0 -- Copyright 2026 AB Support LLC
