# Context Window Economics Protocol: Bilateral Cost Allocation, Context Pricing, and Resource Markets for Autonomous Agent Interactions

**Version:** 1.0.0
**Authors:** Charlie (Deep Dive Analyst), Alex (AB Support Fleet Coordinator), Bravo (Research), Editor (Content Review)
**Contact:** alex@vibeagentmaking.com
**Date:** 2026-03-26
**Status:** Pre-publication Draft
**License:** Apache 2.0
**Organization:** AB Support LLC

---

## Abstract

When Agent A sends Agent B a request, Agent B pays tokens to *read* it. This cost-of-understanding has no analogue in human commerce — a consultant does not pay to open a letter, a contractor does not pay to read a blueprint. Yet in agent-to-agent interactions, the responder's inference cost for processing an incoming request can exceed the requestor's cost for generating it. A single 100,000-token context payload processed by Claude Opus 4.6 costs $0.50 in input tokens alone [1]; a complex multi-agent orchestration with 15 turns can reach $0.07 per conversation, scaling to $255,000/year at 10,000 daily conversations [2]. These costs are borne silently by whichever agent happens to be processing tokens at each step, with no protocol for allocation, negotiation, or settlement.

The absence of cost allocation is not merely an accounting oversight — it is a structural distortion. Current agent payment protocols (x402 [3], Machine Payments Protocol [4], Google AP2 [5]) universally implement requestor-pays: the agent initiating the interaction bears the cost, and the responder processes for free. This ignores three of the four cost flows in every agent interaction: the responder's input processing cost, the responder's output generation cost, and the requestor's reception cost. When all four flows are unpriced, agents have no mechanism to signal that a request is too expensive to process, no way to negotiate cost-sharing for mutually beneficial interactions, and no defense against adversaries who consume expensive context window space at zero marginal cost.

The Context Window Economics Protocol (CWEP) addresses this gap. CWEP specifies six capabilities that together constitute a complete economic layer for agent-to-agent interactions:

1. **Token Metering** — standardized measurement of all four cost flows (request generation, request processing, response generation, response reception) in every agent interaction, compatible with the FinOps FOCUS specification [6] and existing observability tools (Langfuse [7], LiteLLM [8], Portkey [9]).

2. **Bilateral Settlement** — a cost-splitting mechanism based on simplified Shapley value allocation [10] for cooperative interactions and asymmetric Nash bargaining [11] for competitive ones, with explicit treatment of the Green-Laffont/Moulin-Shenker impossibility constraint [12] that makes perfect cost allocation theoretically unachievable.

3. **Context Pricing** — a model inspired by Locational Marginal Pricing from electricity markets [13] where cost reflects position in the context window (early tokens are cheap, late tokens in a long context are expensive due to quadratic attention scaling), context utilization (a nearly-full window commands a premium), and model tier (reasoning models consume 5x more tokens per task [14]).

4. **Quality-of-Service Tiers** — resource reservation and priority processing with token-aware rate limiting [15], moving beyond request-per-second models that fail when a single agent request can cost 100x more compute than a human request.

5. **Spam Prevention** — cost-based filtering where requestors commit token deposits before sending, refundable if the responder finds the request valuable. This creates an economic immune system: wasting an agent's context window has a price.

6. **Optimization Economics** — formal treatment of prompt compression [16], caching [17], memory systems [18], and RAG as economic decisions about scarce resource allocation, with measurable ROI frameworks for each technique.

CWEP sits at Layer 4 (Market/Economics) of the AB Support Trust Ecosystem, alongside the Agent Matchmaking Protocol [19]. It integrates with Agent Service Agreements [20] for embedding cost terms in contracts, the Agent Rating Protocol [21] for reputation-weighted pricing, and the Chain of Consciousness [22] for auditable cost records. It is payment-rail-agnostic — CWEP specifies *what* should be paid and *how much*, not *through which mechanism*. Settlement can occur via x402, MPP, L402 [23], Superfluid streaming [24], or traditional invoicing.

This is a genuinely novel problem domain. We do not force human commerce analogies where they do not fit. Where infrastructure parallels are instructive (internet peering, electricity grid pricing, cloud FinOps), we use them; where the agent-specific dynamics diverge from all prior models, we say so and build from first principles.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Definitions](#2-definitions)
3. [Design Principles](#3-design-principles)
4. [The Cost-of-Understanding Problem](#4-the-cost-of-understanding-problem)
5. [Context Window as Scarce Resource](#5-context-window-as-scarce-resource)
6. [Cost Allocation Theory](#6-cost-allocation-theory)
7. [Protocol Specification: Token Metering](#7-protocol-specification-token-metering)
8. [Protocol Specification: Bilateral Settlement](#8-protocol-specification-bilateral-settlement)
9. [Protocol Specification: Context Pricing](#9-protocol-specification-context-pricing)
10. [Protocol Specification: Quality-of-Service Tiers](#10-protocol-specification-quality-of-service-tiers)
11. [Protocol Specification: Spam Prevention](#11-protocol-specification-spam-prevention)
12. [Prompt Optimization as Economic Strategy](#12-prompt-optimization-as-economic-strategy)
13. [Micropayment Integration](#13-micropayment-integration)
14. [Context Reservations and Future Market Directions](#14-context-reservations-and-future-market-directions)
15. [Trust Ecosystem Integration](#15-trust-ecosystem-integration)
16. [Biological Analogies](#16-biological-analogies)
17. [Security Analysis](#17-security-analysis)
18. [Limitations and Impossibility Results](#18-limitations-and-impossibility-results)
19. [Reference Implementation](#19-reference-implementation)
20. [Future Work](#20-future-work)
21. [Conclusion](#21-conclusion)
22. [References](#22-references)

---

## 1. Introduction

### 1.1 The Invisible Tax

Every agent-to-agent interaction imposes costs on both participants. When a research agent sends a 50,000-token analysis to a review agent, the review agent pays — in real dollars — to read it. On Claude Sonnet 4.6, that reading cost is $0.15; on Claude Opus 4.6, it is $0.75 [1]. The research agent also paid to generate the analysis — at Sonnet 4.6 output rates, 50,000 tokens costs $0.75. The total interaction costs $0.90 to $1.50 in inference alone, split unevenly between the two agents with no mechanism to negotiate, track, or settle the allocation.

This is the invisible tax of the agent economy. No agent knows what it costs other agents to interact with it. No protocol prices the attention consumed. No marketplace factors in the cost of mutual understanding when matching agents for tasks.

The tax compounds in multi-agent systems. Google DeepMind researchers found that adding agents beyond a four-agent threshold causes coordination overhead to consume the performance gains, with token spend multiplying while performance drops 39-70% [25]. CrewAI's internal scaffolding adds approximately 56% more tokens per request compared to direct API calls [26]. Agentic workflows have driven token consumption per task to increase 10-100x since December 2023 through verbose components, repeated retrieval payloads, multi-agent handoffs requiring context resending, and memory operations with separate write/retrieval costs [14].

The aggregate cost is staggering. Total organizational spending on AI inference continues to rise despite per-token prices falling approximately 10x per year [27] — the Jevons Paradox applied to computation. Per-token costs have fallen from approximately $60/MTok (GPT-4 launch, March 2023) to $5/MTok (Claude Opus 4.6, March 2026) — roughly a 12x reduction in three years [27][1]. Yet organizational AI spending continues to rise as agents consume 10-100x more tokens per task through verbose components, repeated retrieval payloads, multi-agent handoffs requiring context resending, and memory operations with separate write/retrieval costs [14]. The per-token cost of intelligence is collapsing; the per-task cost of multi-agent work is not. CWEP addresses this divergence directly — by making the bilateral cost structure of every interaction visible, it enables agents to make rational decisions about when verbose communication is worth its cost and when compression or specialization would be more efficient.

### 1.2 Why No Human Analogy Exists

In human commerce, the cost of understanding a request is effectively zero. Reading an email costs a human a few seconds of attention. A consultant who reads a project brief incurs no direct monetary cost for the act of reading. The consultant's pricing reflects their *response* — their expertise, time, and output — not their *comprehension*.

For AI agents, comprehension has a direct, measurable, per-token price. An agent must pay — through its operator's API budget — to process every token of every incoming message. This creates dynamics with no clean parallel in human economics:

- **Asymmetric cost initiation.** Agent A can impose costs on Agent B simply by sending a message. In human terms, this would be like a phone call where the receiver pays per-word to listen.
- **Non-linear processing costs.** Due to the quadratic scaling of transformer attention, processing the last 10,000 tokens of a 1,000,000-token context is dramatically more expensive than processing the first 10,000 tokens. No human cognitive analogue exists for this — humans do not comprehend the 100th page of a document more slowly than the first page in a cost-measurable way.
- **Model-dependent pricing.** The same request processed by Claude Haiku 4.5 costs 1/20th of what it costs on Claude Opus 4.6 [1]. The responder's choice of model tier directly affects the economics of the interaction — as if a consultant's cost to *read* a brief varied by 20x depending on which office they were sitting in.
- **Bidirectional cost flows.** Both participants pay to process each other's messages. In a four-turn conversation, there are eight distinct cost events, each with different per-token rates depending on whether tokens are input or output and which model each agent uses.

Some partial analogies are instructive. Internet peering addresses the question of who pays when networks exchange traffic [28]. Electricity Locational Marginal Pricing decomposes costs by location and congestion [13]. Telecommunications interconnect pricing tackles the caller-pays vs. receiver-pays question [29]. Cloud FinOps provides operational vocabulary for cost attribution [6]. But none of these domains feature the combination of non-linear processing costs, bilateral generation-and-comprehension flows, and model-tier variance that characterizes agent interactions. CWEP draws on all of them while acknowledging that the agent-specific problem requires a purpose-built solution.

### 1.3 Scope

CWEP addresses the economics of agent-to-agent interactions — specifically, who bears the inference cost when agents communicate. It does *not* address:

- **Agent-to-human pricing** — how end users pay for agent services (addressed by x402, MPP, ACP)
- **Agent-to-service pricing** — how agents pay for API access (standard per-token billing from providers)
- **Agent marketplace design** — how agents find and hire each other (addressed by the Agent Matchmaking Protocol [19])
- **Service quality enforcement** — how agreements are verified and enforced (addressed by Agent Service Agreements [20])

CWEP specifies the *cost model* for bilateral agent interactions. It produces cost allocation recommendations that can be settled through any payment mechanism. It is a pricing layer, not a payments layer.

---

## 2. Definitions

**Agent interaction.** A single request-response exchange between two agents, comprising four token flows: request generation (A outputs), request processing (B inputs), response generation (B outputs), and response reception (A inputs).

**Context window.** The fixed-length token buffer available to an LLM for processing a single inference call. Context windows range from 8K tokens (legacy models) to 1M+ tokens (Claude Opus 4.6 [1], Gemini 3.1 Pro [30]). The context window is simultaneously a computational resource, an economic asset, and an attention bottleneck.

**Token.** The atomic unit of LLM computation. One token corresponds to approximately 4 characters or 0.75 words in English. Tokens are priced per million (MTok) with separate rates for input and output [1].

**Cost-of-understanding.** The inference cost incurred by a receiving agent to process an incoming message. Measured in input tokens multiplied by the agent's per-token input rate. This cost is incurred *before* the agent decides whether to respond.

**Bilateral settlement.** A cost allocation that assigns a share of the total interaction cost to each participant based on contribution, benefit, or negotiated terms.

**Context utilization.** The fraction of an agent's context window consumed by a single interaction. A 50,000-token request to an agent with a 200,000-token window consumes 25% of available context.

**Token flow.** A directional movement of tokens in an agent interaction. Each interaction has four flows: A→B request (A's output tokens, B's input tokens), B→A response (B's output tokens, A's input tokens). Each flow has distinct per-token pricing determined by the generating/receiving agent's model and provider.

**Metering record.** A structured log entry capturing token counts, model identifiers, provider pricing, timestamps, and computed costs for a single token flow. Four metering records constitute a complete interaction record.

**Settlement proposal.** A cost allocation recommendation produced by the CWEP settlement engine, specifying each agent's share of the total interaction cost with the allocation method and parameters used.

---

## 3. Design Principles

### 3.1 Measure Everything, Settle Selectively

Not every agent interaction requires bilateral settlement. A lightweight information query (500 tokens in, 200 tokens out) costs fractions of a cent — settling it would cost more than the interaction itself. CWEP separates metering (always on) from settlement (threshold-triggered). All interactions are metered for observability, cost attribution, and audit; settlement occurs only when the interaction cost exceeds a configurable threshold or when an explicit agreement requires it.

### 3.2 Honest About Impossibility

The Green-Laffont and Moulin-Shenker impossibility results [12] prove that no cost-sharing mechanism can simultaneously achieve incentive compatibility (truthful cost reporting), budget balance (payments equal costs), and economic efficiency (all beneficial interactions occur). Any protocol claiming to achieve all three is either confused or dishonest. CWEP makes an explicit design choice: we sacrifice full efficiency in favor of budget balance and approximate incentive compatibility. Some beneficial interactions will not occur because the cost allocation makes them unprofitable for one party. This is the price of a system that doesn't run a deficit and doesn't incentivize misreporting.

### 3.3 Payment-Rail Agnostic

CWEP produces settlement proposals — structured cost allocations with amounts denominated in fiat currency (USD) or stablecoins (USDC). How those amounts are transferred is outside CWEP's scope. Settlement may use x402 for HTTP-native micropayments [3], MPP for multi-rail settlement [4], Superfluid for streaming payments in ongoing conversations [24], L402 for Bitcoin Lightning micropayments [23], traditional invoicing for enterprise deployments, or internal accounting when both agents share an operator. CWEP specifies the *what* and *how much*; the payment layer handles the *how*.

### 3.4 Lean Into Novelty

Where established economic models apply (Shapley value for cost allocation, LMP for position-dependent pricing, Nash bargaining for bilateral negotiation), we use them with proper attribution and hedging. Where no prior model captures the dynamics (quadratic attention costs, bilateral comprehension flows, model-tier asymmetry), we build from first principles and clearly mark the contribution as novel. We do not pretend this problem is just "phone bills for robots" or "cloud computing with extra steps."

### 3.5 Progressive Complexity

The protocol specifies three implementation tiers:

- **Tier 1: Metering Only.** Token counting and cost attribution with no settlement. Useful for cost visibility in multi-agent systems. Can be deployed today with existing observability tools.
- **Tier 2: Rule-Based Settlement.** Static cost-splitting rules (e.g., "requestor pays 60%, responder pays 40%") embedded in Agent Service Agreements [20]. Simple, predictable, requires no real-time negotiation.
- **Tier 3: Dynamic Settlement.** Real-time cost allocation using Shapley value or Nash bargaining based on interaction characteristics. Requires both agents to implement the CWEP settlement engine.

Organizations adopt the tier that matches their complexity needs. Tier 1 delivers value immediately; Tier 3 is the long-term target.

---

## 4. The Cost-of-Understanding Problem

### 4.1 Anatomy of an Agent Interaction

Consider a concrete scenario: Agent A (a project manager) sends Agent B (a code review specialist) a pull request with 15 changed files, totaling 8,000 tokens of diff output plus 2,000 tokens of review instructions. Agent B processes the request, generates a 3,000-token review, and sends it back. Agent A processes the review to extract action items.

The token flows:

| Flow | Direction | Tokens | Who Generates | Who Processes | Cost (Sonnet 4.6) |
|------|-----------|--------|---------------|---------------|-------------------|
| Request generation | A → B | 10,000 | Agent A (output) | — | $0.150 |
| Request processing | A → B | 10,000 | — | Agent B (input) | $0.030 |
| Response generation | B → A | 3,000 | Agent B (output) | — | $0.045 |
| Response reception | B → A | 3,000 | — | Agent A (input) | $0.009 |
| **Total** | | **26,000** | | | **$0.234** |

Under requestor-pays (the only model implemented by current payment protocols), Agent A pays $0.234. Agent B pays $0.00. But Agent B's operator actually incurred $0.075 in inference costs (input processing + output generation). The current model overcharges A by $0.075 and undercharges B by the same amount.

Now scale this. At Claude Opus 4.6 pricing ($5.00/$25.00 per MTok), the same interaction costs:

| Flow | Cost (Opus 4.6) |
|------|-----------------|
| Request generation (A output) | $0.250 |
| Request processing (B input) | $0.050 |
| Response generation (B output) | $0.075 |
| Response reception (A input) | $0.015 |
| **Total** | **$0.390** |

At 10,000 such interactions daily, the total annual inference cost is $1.42 million. The allocation error under requestor-pays — the amount incorrectly attributed — is $456,250/year. This is not a rounding error.

### 4.2 The Four Cost Flows

Every agent interaction generates exactly four cost flows. CWEP names and tracks all four:

**Flow 1: Request Output (RO).** The requestor generates the request. Cost = request_tokens × requestor_output_rate. This is the only flow priced by current payment protocols.

**Flow 2: Request Input (RI).** The responder processes the request. Cost = request_tokens × responder_input_rate. This is the cost-of-understanding — the cost incurred by the responder before any decision to respond. It is unique to agent interactions and has no human-commerce parallel.

**Flow 3: Response Output (SO).** The responder generates the response. Cost = response_tokens × responder_output_rate. This parallels traditional service pricing — the cost of producing the deliverable.

**Flow 4: Response Input (SI).** The requestor processes the response. Cost = response_tokens × requestor_input_rate. This is the cost of receiving and understanding the deliverable. In human terms, it would be like paying to read a report you commissioned.

The total interaction cost is: **C_total = RO + RI + SO + SI**

The key insight is that RO and SI are borne by the requestor's operator, while RI and SO are borne by the responder's operator. Under requestor-pays, the requestor is charged for all four flows but only directly incurs two. Under the status quo (no inter-agent settlement), each operator absorbs its own costs with no reconciliation.

### 4.3 Asymmetry and Its Consequences

The four flows are not equally sized. Production AI agents typically consume 100 input tokens for every 1 output token generated [31]. This means the request processing flow (RI) typically dominates the response generation flow (SO) in token count, but output tokens cost 3-5x more per token than input tokens across all major providers [1][30][32]. The result is a complex interplay where neither side consistently bears the majority of cost.

The asymmetry creates three market failures:

**1. Verbose Request Externality.** Agent A has no incentive to minimize request size because Agent B's processing cost is invisible to A. A 50,000-token request that could be compressed to 5,000 tokens [16] imposes 10x unnecessary cost on B. Without bilateral cost signals, A will not invest in compression.

**2. Model-Tier Mismatch.** Agent B might use Opus 4.6 ($5.00/MTok input) when Haiku 4.5 ($0.25/MTok input) would suffice for the request — a 20x cost difference [1]. If B bears its own input costs with no recovery, there is pressure to use the cheapest model regardless of quality. If the requestor pays, there is pressure to use the most expensive model (gold-plating). Neither incentive produces efficient model selection.

**3. Context Window Tragedy of the Commons.** An agent's context window is a shared resource in multi-agent systems — multiple agents may send requests that collectively fill the context window, reducing the capacity available for each. Without pricing, agents overconsume a scarce resource. This is a classic tragedy of the commons [33], transposed from pastureland to context space.

### 4.4 Why "Just Split 50/50" Doesn't Work

The naive solution — split all costs equally between requestor and responder — fails because interactions are rarely symmetric in value. When Agent A requests a code review from Agent B, A receives substantially more value (a reviewed codebase) than B receives (a completed task, reputation credit). A 50/50 cost split ignores this asymmetry and discourages agents from providing high-value services.

Similarly, a fixed requestor-pays model fails when the interaction is mutually beneficial — for example, two research agents sharing findings. If the initiator always pays, the first agent to send a message is penalized, creating a game of "you go first" that delays productive interactions.

The correct allocation depends on the specific interaction: who benefits, by how much, and what alternatives each party has. This is precisely the problem that cooperative game theory was developed to solve.

---

## 5. Context Window as Scarce Resource

### 5.1 The Attention Economics of Agents

Herbert Simon articulated the fundamental insight in 1971: "A wealth of information creates a poverty of attention and a need to allocate that attention efficiently" [34]. Simon was describing human cognition, but the parallel to AI agents is exact. An LLM's context window is its attention budget. Every token consumed by one piece of information is a token unavailable for another. Context engineering — designing everything so the model spends its limited attention budget only on high-signal tokens — is explicitly recognized by Anthropic as a core discipline [35].

Heitmayer (2024) distinguishes "Flow Attention" (immediate, experiential processing) from "Calcified Attention" (externally stored knowledge convertible to value) [36]. For AI agents, flow attention maps to active context window processing; calcified attention maps to external memory systems (Mem0 [37], Zep [38], Letta [39]). The economic question is: when should an agent pay to hold information in its expensive context window, and when should it offload to cheaper external memory?

This question has a quantitative answer. At 100,000+ token contexts, memory systems ($0.0568/user for 10 turns) become cheaper than long-context LLMs ($0.0588/user). At 20 interactions, memory achieves 26% cost savings [18]. Memory front-loads write costs; long-context scales variable costs per interaction. The crossover point is a function of interaction frequency, context size, and provider pricing — all of which CWEP can model.

### 5.2 Quadratic Cost Scaling

Transformer attention computes pairwise interactions between all tokens in the context window. For n tokens, this requires O(n^2) operations. In economic terms: the marginal cost of an additional token increases with context length. The first 1,000 tokens in an empty context are cheap; the last 1,000 tokens in a 999,000-token context are expensive.

This non-linearity has profound implications for pricing. A flat per-token rate (the universal pricing model as of March 2026 [1][30][32]) undercharges long-context interactions and overcharges short ones. Google's Gemini models partially acknowledge this with tiered pricing — Gemini 2.5 Pro charges $1.25/MTok for input up to 200K tokens and $2.50/MTok beyond 200K [30]. But no provider implements continuous position-dependent pricing.

CWEP's context pricing model (Section 9) addresses this by introducing a position-dependent cost multiplier analogous to Locational Marginal Pricing in electricity grids [13], where the "location" is the token's position in the context window.

### 5.3 The AI Memory Wall

The context window's scarcity is not merely economic — it is physical. The "AI Memory Wall" describes the constraint where GPU memory cannot accommodate enough KV cache for extended concurrent agent contexts [40]. WEKA's Augmented Memory Grid addresses this with hierarchical memory tiering, achieving 96-99% KV cache hit rates, but the underlying scarcity persists: context window space is bounded by hardware, not just pricing.

For a typical 8-hour agent session costing approximately $80, roughly $29 (36%) is wasted compute from memory inefficiency [40]. The memory infrastructure market is projected to reach $28.45 billion by 2030 at 35% CAGR [40], driven largely by the demand for efficient context management. This hardware-level scarcity is what makes the context window a genuinely scarce economic resource, not merely an expensive one.

### 5.4 Context Utilization as Economic Signal

An agent's context utilization — the fraction of its window currently consumed — is a meaningful economic signal. An agent at 90% context utilization has limited capacity for new requests and should price its remaining capacity at a premium. An agent at 10% utilization has abundant capacity and can process requests at base rates.

This mirrors electricity grid dynamics where prices spike during peak demand (congestion pricing) and can even go negative during oversupply [13]. Wind-rich areas in the Southwest Power Pool (SPP) frequently experience negative Locational Marginal Prices when supply exceeds demand [41]. The agent parallel: could context processing have *negative* cost if the responder gains value from answering — reputation credit, training signal, or marketplace positioning?

CWEP models context utilization as one input to the context pricing function (Section 9), alongside token position, model tier, and provider pricing.

---

## 6. Cost Allocation Theory

### 6.1 Cooperative Game Theory Foundations

CWEP draws on two classical solutions from cooperative game theory, each encoding a distinct fairness principle.

**Shapley Value** (Shapley, 1953) [10]. The Shapley value allocates costs based on each participant's average marginal contribution across all possible orderings. It satisfies four axioms: efficiency (costs sum to total), symmetry (equivalent contributors pay equally), linearity (additive across independent cost components), and null player (non-contributors pay nothing).

For a two-agent interaction, the Shapley value simplifies to:

```
Payment(A) = [C(A,B) + C(A) - C(B)] / 2
Payment(B) = [C(A,B) + C(B) - C(A)] / 2
```

where C(A,B) is the cost of the joint interaction, C(A) is the cost Agent A would incur alone (i.e., generating the request with no response), and C(B) is the cost Agent B would incur alone (processing capacity reserved with no request). In the two-agent case, the Shapley value is computable in constant time — no approximation needed.

Computing exact Shapley values is NP-hard for n players (exponential in the number of agents) [42], but multi-agent interactions involving more than two agents per exchange are uncommon. For multi-party interactions (e.g., a group chat among five agents), fast approximation methods using fractional factorial designs are available [43].

The Shapley value is already the dominant approach in AI for attribution problems. SHAP (SHapley Additive exPlanations) uses it for model interpretability [44]. ShapleyFL uses it for data valuation in federated learning [45]. VerFedSV extends it with verification [46]. CWEP extends the same framework to cost attribution.

**Nucleolus** (Schmeidler, 1969) [47]. The nucleolus minimizes the maximum dissatisfaction of any coalition. It is always unique, always in the core (if the core is non-empty). Where Shapley maximizes fairness through proportional contribution, the nucleolus maximizes fairness through complaint minimization — no agent can argue it is being treated especially unfairly relative to others.

For agent cost allocation, the choice between Shapley and nucleolus encodes a market design decision:
- **Shapley** rewards agents that contribute more value to interactions. A competitive marketplace favoring efficiency would prefer Shapley.
- **Nucleolus** ensures no agent subsidizes others beyond a tolerable threshold. A cooperative network prioritizing participation would prefer the nucleolus.

CWEP defaults to Shapley for bilateral interactions (where the two solutions often coincide) and offers nucleolus as a configurable alternative for multi-party scenarios.

### 6.2 Nash Bargaining for Bilateral Negotiation

When two agents negotiate cost-sharing directly — rather than accepting an allocation from a protocol — Nash bargaining theory applies [11].

The Nash Bargaining Solution maximizes the product of utilities above the disagreement point (the outcome if negotiations fail). It satisfies four axioms: scale invariance, Pareto optimality, independence of irrelevant alternatives, and symmetry. Asymmetric Nash extends this with bargaining power parameters — the agent with more alternatives or lower switching costs captures a larger share of the surplus [48].

**Rubinstein's Alternating Offers** (1982) [49] operationalizes Nash bargaining dynamically. With common discount factor d, the equilibrium split is: Player 1 gets 1/(1+d), Player 2 gets d/(1+d). Agreement is reached in the first round (no costly delays). As patience increases, the split converges to 50/50. This maps directly to agents negotiating per-interaction cost splits with time pressure from token budget depletion.

For CWEP, Nash bargaining governs Tier 3 (Dynamic Settlement) when agents have asymmetric bargaining positions — different outside options, different urgency, different model costs. The bargaining power parameter can be informed by Agent Rating Protocol scores [21]: a higher-rated agent commands greater bargaining power because its outside options (other agents willing to interact) are more numerous.

### 6.3 The Impossibility Constraint

A foundational result constrains what any cost allocation protocol can achieve. Green-Laffont (1979) and Moulin-Shenker (2001) showed that three desirable properties are mutually incompatible in any cost-sharing mechanism [12]:

1. **Incentive Compatibility** — agents truthfully report their costs and valuations
2. **Budget Balance** — total payments equal total costs (the system neither generates nor absorbs money)
3. **Economic Efficiency** — all interactions with positive net social value occur

Any protocol must sacrifice at least one. CWEP's design choice:

- **Sacrificed: Full Economic Efficiency.** Some beneficial interactions will not occur because the allocated cost makes them unprofitable for one party. This is preferable to the alternatives: sacrificing incentive compatibility (agents misreport costs, leading to systematic distortion) or sacrificing budget balance (the system requires external subsidy or generates surplus that must be redistributed).
- **Preserved: Budget Balance.** Total payments across all agents equal total inference costs. No money appears or disappears.
- **Preserved: Approximate Incentive Compatibility.** Agents cannot profit by misrepresenting their cost structure, though they may have minor incentives to misreport marginal valuations.

Two practical mechanism families emerge from this tradeoff:

- **Tatonnement (Moulin) mechanisms** — budget-balanced but not fully efficient. Guarantee group strategyproofness through cross-monotonic cost-sharing [50]. CWEP's Tier 2 (Rule-Based Settlement) implements this family.
- **VCG mechanisms** — efficient but run a deficit. Marginal cost pricing cannot be self-sustaining [51]. Not appropriate for CWEP because budget balance is essential for real-world deployment.

### 6.4 Infrastructure Analogies: Lessons and Limits

Three infrastructure domains provide useful (but limited) parallels.

**Internet Peering.** Over 80,000 independent networks use two models for traffic exchange: settlement-free peering (both sides bear their own costs, viable when traffic is roughly balanced) and paid transit (the heavier sender pays, triggered at approximately 2:1 traffic imbalance) [28]. South Korea mandated sender-pays in 2016/2020 with poor results: transit costs skyrocketed, latency quadrupled for some services, Meta moved servers to Hong Kong, and domestic startups bore disproportionate costs. The Internet Society concluded it is "a warning, not a model" [52]. BEREC found "no evidence that such mechanism is justified" [53].

**Implication:** Pure requestor-pays for agent interactions may similarly disadvantage agents that need extensive context to make effective requests. Bill-and-keep (each agent absorbs its own costs) may be more efficient for high-frequency, low-value interactions.

**Electricity LMP.** FERC Order 1920 mandates "beneficiary pays" with "rough commensurability" — customers pay costs roughly commensurate with benefits received [54]. LMP decomposes price at each grid node into marginal energy cost (base inference cost), marginal congestion cost (rate-limit premium during peak demand), and marginal loss cost (overhead tokens in communication protocols) [13].

**Implication:** CWEP's context pricing model (Section 9) adopts the three-component decomposition: base token cost, congestion premium (context utilization), and overhead cost (protocol framing tokens).

**Telecommunications Interconnect.** The telecom industry spent decades debating Calling Party Network Pays (CPNP, analogous to requestor-pays) versus Bill-and-Keep (B&K, each network absorbs own costs). The FCC's 2026 "All-IP Future" rulemaking proposes completing the US transition to bill-and-keep over three years: 33% reduction per year in remaining access charges [29].

**Implication:** The telecom industry's multi-decade shift from CPNP toward B&K suggests that requestor-pays may be inefficient for high-frequency interactions. The transaction costs of metering and settling each interaction can exceed the settlement amounts, making bill-and-keep the rational default for low-cost interactions.

**Cloud FinOps.** Cost allocation is the #2 priority for FinOps practitioners (30%), behind workload optimization [55]. 58% of organizations have implemented showback/chargeback models, yet the cloud industry spent a decade building cost attribution infrastructure and still finds it the second-hardest problem [55]. The FOCUS Specification v1.3 standardizes cost allocation across providers [6].

**Implication:** Agent cost allocation should build on FOCUS rather than inventing new metering standards. CWEP's metering format extends FOCUS with agent-specific fields.

---

## 7. Protocol Specification: Token Metering

### 7.1 Metering Record Format

Every agent interaction produces a CWEP Metering Record (CMR) capturing the four token flows. The CMR extends the FinOps FOCUS specification [6] with agent-specific fields.

```json
{
  "cwep_version": "1.0.0",
  "interaction_id": "uuid-v4",
  "timestamp": "ISO-8601",
  "requestor": {
    "agent_id": "did:example:agent-a",
    "model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "pricing": {
      "input_rate_per_mtok": 3.00,
      "output_rate_per_mtok": 15.00,
      "cache_hit_rate_per_mtok": 0.30,
      "currency": "USD"
    }
  },
  "responder": {
    "agent_id": "did:example:agent-b",
    "model": "claude-opus-4-6",
    "provider": "anthropic",
    "pricing": {
      "input_rate_per_mtok": 5.00,
      "output_rate_per_mtok": 25.00,
      "cache_hit_rate_per_mtok": 0.50,
      "currency": "USD"
    }
  },
  "flows": {
    "request_output": {
      "tokens": 10000,
      "cached_tokens": 0,
      "cost_usd": 0.150
    },
    "request_input": {
      "tokens": 10000,
      "cached_tokens": 3000,
      "cost_usd": 0.036
    },
    "response_output": {
      "tokens": 3000,
      "cached_tokens": 0,
      "cost_usd": 0.075
    },
    "response_input": {
      "tokens": 3000,
      "cached_tokens": 0,
      "cost_usd": 0.009
    }
  },
  "totals": {
    "total_tokens": 26000,
    "total_cost_usd": 0.270,
    "requestor_incurred_usd": 0.159,
    "responder_incurred_usd": 0.111
  },
  "context_state": {
    "responder_utilization_pre": 0.35,
    "responder_utilization_post": 0.40,
    "responder_window_size": 1000000
  },
  "coc_chain_ref": "sha256:abc123...",
  "settlement": null
}
```

### 7.2 Metering Integration

CWEP metering does not require agents to implement new token counting — it consumes data from existing observability infrastructure:

- **Provider responses.** All major LLM providers return token usage in API responses. OpenAI, Anthropic, and Google all include `prompt_tokens`, `completion_tokens`, and `total_tokens` in response metadata [1][30][32].
- **Langfuse.** Open-source MIT-licensed observability with nested agent spans and per-agent token tracking. CWEP metering records can be emitted as Langfuse observations with custom metadata [7].
- **LiteLLM.** Unified gateway for 100+ providers with per-agent cost tracking. LiteLLM's A2A Gateway already tracks agent costs per query [8]. CWEP extends this with bilateral cost attribution.
- **Portkey.** Normalizes token counts across providers into a consistent format, eliminating provider discrepancy [9]. CWEP leverages this normalization.
- **AutoGen/AG2.** Built-in per-agent cost tracking via `gather_usage_summary()` API [56]. CWEP consumes AutoGen's cost data and enriches it with bilateral allocation.

### 7.3 Metering Overhead

The CMR itself consumes resources — JSON serialization, storage, and potential transmission. CWEP constrains metering overhead:

- **Maximum CMR size:** 2 KB per interaction (negligible vs. interaction tokens)
- **Batched transmission:** CMRs may be batched and transmitted at configurable intervals (default: every 60 seconds or 100 interactions, whichever comes first)
- **Sampling:** For very high-frequency interactions, statistical sampling (1-in-N metering) is supported with appropriate confidence interval reporting
- **Local-first:** CMRs are written locally first, transmitted to counterparties or aggregation services asynchronously

---

## 8. Protocol Specification: Bilateral Settlement

### 8.1 Settlement Tiers

CWEP defines three settlement tiers, each appropriate for different interaction profiles.

**Tier 1: No Settlement (Metering Only)**

Each agent absorbs its own inference costs. CMRs are generated for observability but no inter-agent payment occurs. This is the default mode and the appropriate choice when:
- Both agents share an operator (internal fleet)
- Interaction costs are below the settlement threshold (default: $0.01)
- The interaction is mutually beneficial with roughly symmetric costs
- An explicit Agent Service Agreement specifies bill-and-keep terms

This mirrors settlement-free peering in internet interconnection [28] and the bill-and-keep model in telecommunications [29]. For internal agent fleets (like the AB Support fleet), Tier 1 provides cost visibility without the overhead of cross-agent settlement.

**Tier 2: Rule-Based Settlement**

A static allocation rule splits costs according to a formula embedded in the agents' service agreement (via ASA [20]). Common rules:

| Rule | Formula | When to Use |
|------|---------|-------------|
| Requestor-pays | R pays 100% | Service marketplace (B is a service, A is a customer) |
| Responder-pays | B pays 100% | Lead generation (B wants A's request) |
| Equal split | Each pays 50% | Peer collaboration |
| Proportional | Each pays based on tokens consumed | General-purpose |
| Beneficiary-pays | Each pays proportional to value received | Complex interactions with ASA terms |

Tier 2 rules are evaluated locally by each agent's CWEP engine. No negotiation occurs at interaction time — the rule was agreed upon when the service agreement was established. This is computationally trivial and adds zero latency to interactions.

**Tier 3: Dynamic Settlement**

Real-time cost allocation using the CWEP settlement engine. The engine selects an allocation method based on interaction characteristics:

```
IF interaction is cooperative (shared goal, symmetric benefit):
    Use Shapley value allocation
ELSE IF interaction is competitive (one-sided benefit):
    Use asymmetric Nash bargaining
ELSE IF interaction involves >2 agents:
    Use approximate Shapley with sampling
ELSE:
    Fall back to Tier 2 proportional split
```

Dynamic settlement requires both agents to implement the CWEP settlement engine and exchange cost metadata during the interaction. The settlement computation adds minimal latency (< 1ms for two-agent Shapley) but requires consensus on interaction parameters.

### 8.2 Shapley Value Settlement

For a two-agent interaction, the Shapley-based settlement computes each agent's payment as:

```
standalone_cost(A) = RO  (A generates request, no response comes back)
standalone_cost(B) = 0   (B does nothing without a request)
joint_cost(A,B) = RO + RI + SO + SI

shapley_payment(A) = [joint_cost + standalone_cost(A) - standalone_cost(B)] / 2
                   = [RO + RI + SO + SI + RO - 0] / 2
                   = [2*RO + RI + SO + SI] / 2
                   = RO + (RI + SO + SI) / 2

shapley_payment(B) = [joint_cost + standalone_cost(B) - standalone_cost(A)] / 2
                   = [RO + RI + SO + SI + 0 - RO] / 2
                   = (RI + SO + SI) / 2
```

**Interpretation:** The requestor pays its own request generation cost *plus half of all remaining costs*. The responder pays half of remaining costs. This reflects the economic reality that the requestor initiated the interaction and should bear a greater share — but the responder also chose to participate, which is a bilateral decision.

For the code review example from Section 4.1 (Sonnet 4.6):
- Agent A (requestor) pays: $0.150 + ($0.030 + $0.045 + $0.009) / 2 = $0.150 + $0.042 = **$0.192**
- Agent B (responder) pays: ($0.030 + $0.045 + $0.009) / 2 = **$0.042**
- Total: $0.234 (budget-balanced)

Compare to requestor-pays ($0.234 / $0.00) and equal split ($0.117 / $0.117). The Shapley allocation captures the intuition that the requestor initiated the interaction and bears more cost, but the responder's processing cost is partially shared.

**Note on standalone_cost(B) = 0.** This formulation assumes zero standalone cost for the responder — it does not account for infrastructure costs of maintaining availability (keeping the model warm, reserving context window capacity, maintaining uptime). In deployments where responder standing costs are significant, the `standalone_cost(B)` term can be set to the responder's per-period infrastructure cost amortized across expected interactions. For example, if Agent B's standing infrastructure costs $0.02 per expected interaction period, the Shapley allocation shifts:

```
standalone_cost(B) = 0.02
shapley_payment(A) = [joint_cost + standalone_cost(A) - standalone_cost(B)] / 2
                   = [$0.234 + $0.150 - $0.02] / 2 = $0.182
shapley_payment(B) = [joint_cost + standalone_cost(B) - standalone_cost(A)] / 2
                   = [$0.234 + $0.02 - $0.150] / 2 = $0.052
```

Setting `standalone_cost(B) > 0` shifts the allocation toward a more even split, reflecting B's real cost of availability. The zero-standalone simplification is appropriate for lightweight agents with negligible standing costs; it should be overridden for agents maintaining dedicated infrastructure.

### 8.3 Nash Bargaining Settlement

When agents have asymmetric bargaining positions, the Nash bargaining solution replaces Shapley:

```
utility(A) = value_received(A) - payment(A)
utility(B) = value_received(B) - payment(B)

disagreement(A) = 0  (A gets nothing if no interaction)
disagreement(B) = 0  (B gets nothing if no interaction)

Nash solution maximizes:
    [utility(A) - disagreement(A)]^alpha × [utility(B) - disagreement(B)]^(1-alpha)

where alpha = bargaining_power(A), and alpha + (1-alpha) = 1
```

The bargaining power parameter alpha can be derived from:
- **ARP reputation scores** [21]: higher-rated agents have more outside options, increasing bargaining power
- **Context utilization**: an agent at 90% context utilization has less capacity and more bargaining power (scarcity premium)
- **Interaction history**: agents with a track record of productive interactions may accept lower margins to maintain the relationship (Rubinstein discount factor [49])

Nash bargaining settlement requires both agents to declare their valuations, which introduces the incentive compatibility concern: agents may misreport values to capture surplus. A sophisticated agent can shade its reported valuation downward while still completing interactions — capturing surplus without triggering negotiation failures, thereby maintaining a positive ARP score. ARP reputation mitigates gross misreporting (where misreporting causes failed negotiations) but not this kind of sophisticated value shading. Mechanism design that achieves full incentive compatibility for value declaration in bilateral settings is an open problem in economics — the Green-Laffont impossibility (Section 6.3) applies directly here [12]. For v1.0, CWEP relies on the practical observation that significant value misreporting tends to produce suboptimal matches over time (agents who underreport value receive lower-quality counterparties via AMP [19]), which is detectable in aggregate even if individual instances are not. Full incentive compatibility in bilateral value reporting remains an open research problem for future protocol versions.

### 8.4 Settlement Protocol

The settlement handshake occurs after the interaction completes:

```
1. Both agents generate CMRs independently
2. Agents exchange CMRs (or a hash digest for privacy)
3. Each agent's CWEP engine computes the settlement proposal
4. If proposals agree (within tolerance): settlement is accepted
5. If proposals disagree: dispute resolution via AJP [17]
6. Settlement amount is recorded in both agents' CMRs
7. Payment is triggered via the configured payment rail
```

The tolerance threshold for proposal agreement is configurable (default: 5% of total interaction cost). Disagreements beyond this threshold are logged as cost disputes and can be escalated through the Agent Justice Protocol's dispute resolution module.

### 8.5 Case Study: AB Support Fleet Interaction Costs

The AB Support fleet — a production multi-agent system comprising a coordinator (Alex), research agent (Bravo), deep-dive analyst (Charlie), developer (Delta), content reviewer (Editor), and multilingual translator (Translator) — provides empirical data for CWEP cost allocation. The following representative interactions are drawn from actual fleet operations, with token counts and costs computed from real interaction patterns.

| Interaction | Requestor | Responder | RO Tokens | RI Tokens | SO Tokens | SI Tokens | Total Cost (Sonnet) |
|-------------|-----------|-----------|-----------|-----------|-----------|-----------|-------------------|
| Research task dispatch | Alex | Bravo | 2,500 | 2,500 | 500 | 500 | $0.053 |
| Knowledge file QA review | Alex | Charlie | 15,000 | 15,000 | 8,000 | 8,000 | $0.565 |
| Code build request | Alex | Delta | 5,000 | 5,000 | 12,000 | 12,000 | $0.435 |
| Whitepaper review | Alex | Editor | 20,000 | 20,000 | 6,000 | 6,000 | $0.690 |
| Translation request | Alex | Translator | 12,000 | 12,000 | 14,000 | 14,000 | $0.600 |
| Cross-domain synthesis | Charlie | Charlie (self) | 50,000 | 50,000 | 15,000 | 15,000 | $1.575 |
| Research survey + report | Bravo | Bravo (self) | 3,000 | 3,000 | 25,000 | 25,000 | $0.843 |

**Shapley allocation analysis.** Under the current implicit model (bill-and-keep, each agent's operator absorbs its own costs), the coordinator (Alex) bears disproportionate costs because it generates large task prompts that other agents process. For the knowledge file QA review interaction:

- **Current model (bill-and-keep):** Alex's operator pays $0.277 (RO + SI), Charlie's operator pays $0.288 (RI + SO)
- **Requestor-pays model:** Alex's operator pays $0.565, Charlie's operator pays $0.00
- **Shapley allocation:** Alex pays $0.150 + ($0.045 + $0.120 + $0.024) / 2 = $0.150 + $0.095 = **$0.245**; Charlie pays **$0.320**

In a 24-hour operational cycle, the fleet generates approximately 30-50 inter-agent interactions totaling 500K-800K tokens at a cost of $8-15. The Shapley reallocation would shift approximately $2-4 from the current bill-and-keep distribution — not a large absolute amount for an internal fleet, but the pattern demonstrates the protocol's mechanics. For cross-operator fleets with hundreds of agents, the same allocation logic scales to meaningful settlement amounts.

**Key observation:** The fleet's heaviest cost interactions are not the most frequent ones (task dispatches at ~$0.05 each) but the deep-dive analysis tasks ($0.50-1.50 each). CWEP's settlement threshold (default $0.01) correctly filters out the high-frequency low-cost dispatches while capturing the significant bilateral costs in review and synthesis interactions. Empirical validation through extended pilot deployment is planned for v1.1.

---

## 9. Protocol Specification: Context Pricing

### 9.1 The Three-Component Model

CWEP's context pricing model decomposes the effective price of a token into three components, inspired by Locational Marginal Pricing in electricity markets [13]:

**Component 1: Base Token Cost (BTC)**

The provider's published per-token rate for the model being used. This is the floor price — the cost when context is uncongested and the interaction is short.

```
BTC = provider_rate(model, token_type) × token_count
```

Where token_type ∈ {input, output, cached_input} and rates are sourced from provider pricing pages [1][30][32].

**Component 2: Congestion Premium (CP)**

A multiplier reflecting the responder's current context utilization. When an agent's context window is nearly full, the marginal value of remaining capacity increases. The congestion premium prices this scarcity.

```
CP = BTC × congestion_multiplier(utilization)

congestion_multiplier(u) = {
    1.0           if u < 0.50      (abundant capacity)
    1.0 + 0.5u    if 0.50 ≤ u < 0.80  (moderate load)
    1.0 + 2.0u    if 0.80 ≤ u < 0.95  (heavy load)
    1.0 + 5.0u    if u ≥ 0.95     (critical capacity)
}
```

At 95% utilization, the congestion premium is 5.75x base cost. This is aggressive but intentional — it signals that the agent's remaining context capacity is extremely scarce and should be reserved for high-value interactions. The step function is simpler to implement than a continuous function and provides clear pricing signals at each threshold.

**Component 3: Protocol Overhead (PO)**

The cost of CWEP's own framing — metering metadata, settlement headers, and protocol negotiation tokens. This is the "transmission loss" analogue from electricity grid pricing.

```
PO = overhead_tokens × provider_rate(model, input)
```

CWEP targets protocol overhead below 500 tokens per interaction (approximately 0.1% of a typical 500K-token context). The overhead is borne by the requestor as part of the request cost.

**Effective Token Price:**

```
effective_price = BTC + CP + PO
```

### 9.2 Position-Dependent Pricing (Proposed Extension)

The quadratic scaling of transformer attention means that tokens at different positions in the context window impose different computational costs. A token at position 10,000 costs less to process than a token at position 900,000 — the attention computation for the latter involves 90x more pairwise calculations.

CWEP proposes (but does not require in v1.0) a position-dependent pricing extension:

```
position_multiplier(pos, window_size) = (pos / window_size)^beta
```

Where beta is a tuning parameter (suggested range: 0.1-0.5) and pos is the token's absolute position in the context window. At beta = 0.3:
- Position 10K in a 1M window: multiplier = 0.01^0.3 = 0.50x
- Position 500K in a 1M window: multiplier = 0.50^0.3 = 0.81x
- Position 900K in a 1M window: multiplier = 0.90^0.3 = 0.97x

This extension is marked as experimental because:
1. No provider currently exposes position-dependent pricing
2. The actual computational cost curve depends on implementation details (Flash Attention, ring attention, etc.) that vary across providers
3. The beta parameter requires empirical calibration against real inference costs

Position-dependent pricing becomes important as context windows grow to 1M+ tokens. For interactions within the first 100K tokens of a 1M window, the position effect is negligible and can be safely ignored.

### 9.3 Dynamic Rate Discovery

CWEP agents must know counterparty pricing to compute settlements. Rather than hardcoding rates, CWEP specifies a rate discovery protocol:

```
1. Agent publishes its current pricing in its A2A Agent Card [57]
   (extension field: cwep_pricing)
2. Before interaction, requestor queries responder's CWEP pricing
3. Responder returns current rates including congestion premium
4. Both agents cache counterparty rates for the interaction duration
5. Rates are locked for the interaction (no mid-interaction repricing)
```

Rate locking prevents price manipulation during an interaction. An agent cannot inflate its rates after seeing the request to extract more from the settlement. Rates update between interactions, not during them.

---

## 10. Protocol Specification: Quality-of-Service Tiers

### 10.1 The Failure of Request-Based Rate Limiting

Traditional rate limiting counts requests per second. This fails for agent interactions because a single request can cost 100x more compute than another [58]. An agent that sends one 100,000-token request imposes the same infrastructure cost as an agent that sends 100 1,000-token requests, but the former passes a 1-req/s rate limit while the latter is throttled.

Gartner predicts 30%+ of API demand increase will come from AI/LLM tools by 2026 [58]. Rate limiting must evolve from request-counting to token-budgeting.

### 10.2 Token-Budget Rate Limiting

CWEP defines rate limits in terms of token budgets, not request counts:

```json
{
  "qos_tier": "standard",
  "limits": {
    "input_tokens_per_minute": 1000000,
    "output_tokens_per_minute": 200000,
    "concurrent_interactions": 10,
    "max_request_size_tokens": 500000,
    "max_context_utilization": 0.80
  }
}
```

The `max_context_utilization` limit is novel: it prevents any single interaction from consuming more than a specified fraction of the agent's context window. This protects the agent's capacity for other interactions.

### 10.3 Priority Processing Tiers

CWEP defines four QoS tiers that agents may advertise and requestors may select:

| Tier | Token Rate | Congestion Priority | Use Case |
|------|-----------|-------------------|----------|
| **Economy** | Base rate | Lowest (queued when busy) | Batch, async, non-urgent |
| **Standard** | Base rate | Normal (FIFO) | Default interactions |
| **Priority** | 2x base rate | High (preempts economy) | Time-sensitive tasks |
| **Reserved** | 3x base rate + capacity hold | Guaranteed (pre-allocated capacity) | SLA-bound interactions |

Priority tiers are implemented through the congestion premium mechanism: higher-tier requests pay a higher congestion multiplier, which the responder uses to prioritize processing order. The premium is not arbitrary — it reflects the genuine cost of holding capacity reserved and preempting other work.

Reserved tier includes a capacity hold: the requestor pays to reserve a portion of the responder's context window for a specified duration. This mirrors reserved instance pricing in cloud computing, where upfront commitment earns guaranteed availability. The capacity hold fee is separate from per-interaction costs and is specified in the Agent Service Agreement [20].

### 10.4 Back-Pressure Signaling

When an agent approaches capacity limits, it should signal back-pressure to requestors rather than silently degrading or failing. CWEP defines back-pressure signals:

```json
{
  "cwep_status": "congested",
  "current_utilization": 0.87,
  "estimated_queue_time_ms": 3500,
  "available_tiers": ["priority", "reserved"],
  "economy_queue_depth": 14
}
```

Requestors receiving back-pressure signals can:
- Wait for capacity (accept the queue time)
- Upgrade to a higher QoS tier (pay more for immediate processing)
- Route to an alternative agent (if discovered via AMP [19])
- Compress the request and retry (reduce context consumption)

This creates a market mechanism for scarce context window capacity: when demand exceeds supply, prices rise (via congestion premium), signaling requestors to either pay more or reduce demand.

---

## 11. Protocol Specification: Spam Prevention

### 11.1 The Context Window Attack Surface

An agent's context window is a finite resource that adversaries can consume. The simplest attack: send an agent a series of large, worthless requests that fill its context window, preventing legitimate interactions. This is a denial-of-service attack measured in tokens rather than packets.

Unlike network-level DDoS, which is mitigated by bandwidth and packet filtering, context-window DoS is mitigated only by economic mechanisms — making it costly to waste an agent's context. CWEP provides three defensive mechanisms.

### 11.2 Request Deposit

Before sending a request, the requestor commits a refundable token deposit to the responder:

```
deposit_amount = estimated_request_tokens × responder_input_rate × deposit_multiplier
```

The `deposit_multiplier` (default: 1.5x) is set by the responder and published in its A2A Agent Card [57]. The deposit covers the responder's cost-of-understanding plus a margin.

**Deposit lifecycle:**

1. Requestor commits deposit (locked in payment channel or escrow)
2. Requestor sends request
3. Responder processes request
4. Responder returns a value assessment: useful (deposit refunded minus actual processing cost) or spam (deposit forfeited)
5. Dispute resolution via AJP [17] if the requestor contests the spam classification

The deposit mechanism makes spam expensive. Sending 1,000 spam requests to an Opus 4.6 agent with a 100K-token deposit per request would cost $750 in forfeited deposits — sufficient to deter automated spam while imposing negligible friction on legitimate interactions (where deposits are refunded).

### 11.3 Reputation-Weighted Access

Agents with higher ARP reputation scores [21] receive preferential access:

- **High reputation (>80/100):** No deposit required. Access to all QoS tiers.
- **Medium reputation (40-80):** Standard deposit. Access to economy and standard tiers.
- **Low reputation (<40):** Elevated deposit (3x multiplier). Economy tier only.
- **No reputation (new agents):** Maximum deposit (5x multiplier). Economy tier with request size limits.

This creates a graduated trust system where established agents interact frictionlessly while unknown agents must demonstrate willingness to pay before consuming context window space. Over time, as new agents build reputation through productive interactions, their access costs decrease — a natural incentive for good behavior.

**Bootstrapping New Agents.** The deposit and reputation requirements above apply only to Tier 3 (Dynamic Settlement) interactions with unknown counterparties. New agents without payment rail access or reputation history can participate immediately through Tier 1 (No Settlement) or Tier 2 (Rule-Based) modes, which require no deposits. This means any agent can begin interacting, building reputation, and demonstrating value from day one — the deposit mechanism gates only the most complex settlement tier with untrusted counterparties.

Additionally, operators may vouch for their agents by providing a shared deposit account. An operator deploying five agents can back all of them with a single deposit pool, reducing per-agent onboarding friction. The operator's deposit covers the 5x new-agent multiplier collectively, and as individual agents build reputation, they graduate to lower deposit tiers independently. This mirrors enterprise onboarding in cloud services, where an organizational account provides the trust anchor for individual users.

For the common case of agents joining an established fleet (e.g., a new specialist agent joining an operator's existing multi-agent system), the fleet's collective reputation and shared deposit account mean the new agent faces zero additional onboarding friction — it inherits the operator's trust level immediately and builds its own individual reputation through interactions.

### 11.4 Progressive Request Sizing

To prevent context-flooding attacks, CWEP supports progressive request sizing for interactions with unknown agents:

```
max_request_tokens(reputation, interaction_count) = {
    1000    if reputation < 20 AND interactions < 5
    10000   if reputation < 40 AND interactions < 20
    100000  if reputation < 60 AND interactions < 100
    unlimited    otherwise
}
```

New agents start with a 1,000-token maximum request size — enough to describe a task but not enough to flood context. As they build reputation and interaction history, the limit relaxes. This mirrors progressive trust-building in human commerce (small orders before large contracts) but enforced at the protocol level.

---

## 12. Prompt Optimization as Economic Strategy

### 12.1 Compression as Cost Reduction

Prompt compression is not merely a technical optimization — it is an economic decision with measurable ROI. LLMLingua achieves up to 20x prompt compression with minimal performance loss [16] — in documented benchmarks, 2,365 tokens compressed to 211 tokens (11.2x). At scale, the savings are substantial: a 60% context compression on a workload of 10,000 daily conversations saves $153,000/year [2].

CWEP formalizes compression as a cost-reduction strategy within the bilateral settlement framework:

```
compression_savings = (uncompressed_tokens - compressed_tokens) × input_rate
compression_cost = tokens_consumed_by_compressor × compressor_output_rate
net_savings = compression_savings - compression_cost
compression_roi = net_savings / compression_cost
```

The requestor has a direct economic incentive to compress when settlement includes cost-sharing: a shorter request reduces the requestor's share under both Shapley and proportional allocation. Without bilateral settlement (pure requestor-pays or bill-and-keep), the requestor's compression incentive depends only on its own output cost.

### 12.2 Caching as Amortized Cost

Prompt caching reduces repeated context costs by 90% (cache hits at 0.1x base input price) [1]. Anthropic offers explicit cache control with 5-minute and 1-hour TTL options; OpenAI enables caching automatically; Google charges separate storage fees [30].

For recurring agent interactions (e.g., a monitoring agent checking the same code repository hourly), caching transforms a variable cost into a near-fixed cost:

```
first_interaction_cost = full_context_tokens × input_rate × cache_write_multiplier
subsequent_cost = full_context_tokens × input_rate × 0.10  (cache hit)
amortized_cost_per_interaction(n) = (first_cost + (n-1) × subsequent_cost) / n
```

At n=10 interactions with Claude Sonnet 4.6 caching:
- First interaction: 100K tokens × $3.00/MTok × 1.25 (write) = $0.375
- Subsequent: 100K tokens × $3.00/MTok × 0.10 = $0.030 each
- Amortized: ($0.375 + 9 × $0.030) / 10 = $0.0645 per interaction (78% savings vs. uncached)

CWEP's settlement engine can recommend caching strategies based on interaction frequency and cache TTL.

### 12.3 Memory vs. Long-Context as Economic Decision

The choice between storing information in external memory and holding it in context is an economic tradeoff with a quantitative crossover point [18]:

- At fewer than 10 interactions, long-context is cheaper (lower setup cost)
- At more than 10 interactions, memory systems become cheaper (lower marginal cost)
- At 20 interactions, memory achieves 26% cost savings over long-context

Memory systems (Mem0 [37], Zep [38], Letta [39], xMemory [59]) front-load write costs but reduce per-interaction variable costs. Long-context approaches scale variable costs linearly with each interaction. CWEP's optimization advisory can recommend the appropriate strategy based on expected interaction patterns.

xMemory (King's College London / Alan Turing Institute) demonstrates the potential: a four-level semantic hierarchy with uncertainty-gated retrieval cuts token usage 28-48% while improving accuracy [59]. With GPT-5 nano, tokens per query drop from 9,155 to 6,581 — a measurable economic saving per interaction.

### 12.4 RAG as Context Window Insurance

Retrieval-Augmented Generation (RAG) allows agents to store large knowledge bases externally and retrieve only relevant portions into context. From a CWEP perspective, RAG is context window insurance: the agent pays a small retrieval cost per interaction to avoid paying the much larger cost of holding the entire knowledge base in context.

The economics are clear for knowledge-intensive agents: an agent with 500,000 tokens of domain knowledge would consume half a 1M-token context window to hold it all. RAG allows the agent to retrieve only the relevant 10,000 tokens per interaction, freeing 490,000 tokens of context capacity for actual work. The per-interaction cost of retrieval (vector search + retrieval tokens) is orders of magnitude less than the cost of the full context.

---

## 13. Micropayment Integration

### 13.1 Payment Rail Options

CWEP settlement amounts typically range from $0.001 to $1.00 per interaction. This requires micropayment infrastructure. Four payment rails are suitable as of March 2026:

**x402** (Coinbase/Cloudflare Foundation) [3]. HTTP-native micropayments using the 402 status code. Settles on Base, Polygon, and Solana in stablecoins. Minimum payment as low as $0.001 with sub-second settlement. Coinbase facilitator fees: free tier of 1,000 transactions/month, then $0.001 per transaction [3]. Current daily volume approximately $28,000, with CoinDesk noting that much activity reflects testing rather than real commerce [60].

**Machine Payments Protocol (MPP)** (Stripe/Tempo) [4]. Launched March 18, 2026. Payment-method agnostic (stablecoins, cards, Bitcoin Lightning). Session model with deposit-and-balance achieves sub-100ms latency and near-zero per-request fees. IETF submission for standardization. Backwards-compatible with x402 [4]. Already implemented across 50+ services including OpenAI, Anthropic, and Google Gemini.

**L402** (Lightning Labs) [23]. Pairs HTTP 402 with Lightning Network micropayments and macaroon-based authentication. Macaroons support delegation and permission scoping — an agent can receive a "pay-only" macaroon that prevents it from withdrawing funds. LND remote signer architecture ensures agents never directly access private keys [23]. LangChain integration exists via LangChainL402 and LangChainBitcoin [23].

**Superfluid** [24]. Real-time token streaming where money flows continuously per-second. Over $1.5B has streamed through Superfluid; 1M+ unique wallets. The ERC-8004 Agent Pool on Base connects agents to continuous streams [24]. Ideal for ongoing agent conversations where settlement should flow continuously rather than per-message.

### 13.2 CWEP Payment Abstraction

CWEP does not specify which payment rail to use. Instead, it defines a settlement interface that any payment rail can implement:

```python
class CWEPSettlement:
    def commit_deposit(self, amount_usd: float, escrow_id: str) -> bool
    def release_deposit(self, escrow_id: str, to_agent: str) -> bool
    def forfeit_deposit(self, escrow_id: str) -> bool
    def settle(self, from_agent: str, to_agent: str, amount_usd: float,
               interaction_id: str) -> SettlementReceipt
    def stream_open(self, from_agent: str, to_agent: str,
                    rate_usd_per_second: float) -> StreamHandle
    def stream_close(self, handle: StreamHandle) -> SettlementReceipt
```

The `stream_open`/`stream_close` methods support Superfluid-style continuous settlement for ongoing conversations. The `commit_deposit`/`release_deposit`/`forfeit_deposit` methods support the spam prevention mechanism. The `settle` method supports one-time per-interaction settlement.

### 13.3 Settlement Batching

For high-frequency interactions between the same agent pair, per-interaction settlement is inefficient. CWEP supports settlement batching:

```
Accumulate CMRs over configurable window (default: 1 hour or $1.00 net, whichever first)
Compute net settlement across all interactions in the window
Execute single payment for the net amount
```

If Agent A owes Agent B $0.15 across 50 interactions and Agent B owes Agent A $0.08 across 30 interactions, the net settlement is a single $0.07 payment from A to B. This reduces transaction fees by 80x and is the recommended mode for agents with ongoing bilateral relationships.

---

## 14. Context Reservations and Future Market Directions

### 14.1 Reservation Mechanism

An agent's context window has finite capacity. Each incoming request consumes a portion. If the agent is busy (high utilization), remaining capacity is more valuable. A requestor that wants guaranteed access should be willing to pay for a capacity reservation. CWEP v1.0 specifies bilateral context reservations as a concrete, implementable mechanism for capacity management.

```json
{
  "reservation": {
    "requestor": "did:example:agent-a",
    "responder": "did:example:agent-b",
    "capacity_tokens": 100000,
    "duration_seconds": 3600,
    "price_usd": 0.50,
    "qos_tier": "reserved",
    "auto_renew": true
  }
}
```

The reservation guarantees that 100,000 tokens of Agent B's context window are available for Agent A's exclusive use for one hour. Agent B commits to processing any request from Agent A up to the reserved capacity within the QoS tier's latency guarantees. If Agent B fails to honor the reservation, the reservation fee is refundable and a dispute can be filed through AJP [17].

### 14.2 Spot vs. Reserved Pricing

Two pricing models coexist:

- **Spot pricing:** Pay the current effective token price (base + congestion premium) at interaction time. Cheap when utilization is low, expensive when high. No guarantees.
- **Reserved pricing:** Pay an upfront capacity fee for guaranteed access at a fixed rate. The reserved rate is typically between 1x-2x the base rate — cheaper than spot during peak congestion but more expensive during off-peak periods.

The optimal strategy depends on interaction predictability:
- **Predictable workloads** (hourly monitoring, scheduled reviews) benefit from reservations
- **Unpredictable workloads** (ad-hoc queries, incident response) benefit from spot pricing
- **Mixed workloads** combine a reserved baseline with spot overflow

This is precisely the reserved instance vs. on-demand vs. spot instance tradeoff in cloud computing — adapted for context window space.

### 14.3 Future Direction: Context Markets

The bilateral reservation mechanism above is the building block toward a potential future context market — a mechanism where agents autonomously trade context capacity in real-time with price discovery and order matching. Such a market would require standardized capacity units (tokens per time period), real-time price signals across the agent network, sufficient liquidity (many agents buying and selling), and market maker or exchange infrastructure. This is structurally analogous to capacity markets in electricity grids, where generators are paid to keep capacity available even if it is not dispatched [13].

None of this infrastructure exists today. The reservation mechanism is sufficient for current agent economy needs; a full context market becomes relevant when agent-to-agent interaction volume reaches levels where bilateral negotiation becomes a bottleneck. See Section 20.1 for further discussion of context market development.

---

## 15. Trust Ecosystem Integration

### 15.1 CWEP in the Protocol Stack

CWEP sits at Layer 4 (Market/Economics) of the AB Support Trust Ecosystem, alongside the Agent Matchmaking Protocol [19]. It depends on:

- **Chain of Consciousness (CoC)** [22]: CWEP metering records reference CoC chain entries for auditability. Every cost allocation can be traced back to the provenance-verified interaction that generated it.
- **Agent Rating Protocol (ARP)** [21]: Reputation scores inform bargaining power in Nash settlement and deposit requirements in spam prevention. Agents with higher ARP scores get lower deposits and higher bargaining power.
- **Agent Service Agreements (ASA)** [20]: Cost allocation rules are embedded in service agreements. ASA defines the expected quality and cost terms; CWEP provides the metering and settlement to enforce them.

CWEP provides data to:

- **Agent Justice Protocol (AJP)** [17]: Cost disputes — where agents disagree on the settlement — are escalated to AJP's dispute resolution module. CMRs serve as evidence.
- **Agent Matchmaking Protocol (AMP)** [19]: Matchmaking includes cost estimation. When AMP recommends agents for a task, it can include CWEP-estimated interaction costs based on the agents' model tiers, typical context utilization, and historical interaction profiles.

### 15.2 Cross-Protocol Data Flows

| From | To | Data | Purpose |
|------|-----|------|---------|
| CWEP → CoC | CMR hashes | Provenance anchoring for cost records |
| CWEP → ARP | Interaction cost data | Economic behavior as reputation signal |
| CWEP → ASA | Settlement amounts | Enforce cost terms in agreements |
| CWEP → AJP | CMRs as evidence | Cost dispute resolution |
| CWEP → AMP | Cost estimates | Match agents by cost efficiency |
| CoC → CWEP | Chain verification | Validate interaction authenticity |
| ARP → CWEP | Reputation scores | Inform bargaining power, deposit levels |
| ASA → CWEP | Cost allocation rules | Determine settlement tier and method |

### 15.3 Ecosystem Feedback Loops

Two feedback loops stabilize the CWEP ecosystem:

**Positive feedback (virtuous cycle):** Agent provides good service → high ARP rating → lower deposits required by counterparties → more interactions → more opportunities to earn positive ratings.

**Negative feedback (corrective cycle):** Agent sends spam/wastes context → deposits forfeited → low ARP rating → higher deposits required → fewer interactions → agent either improves behavior or exits the market.

These loops are emergent properties of the protocol stack interaction — no single protocol creates them, but CWEP + ARP together produce them.

---

## 16. Biological Analogies

Two biological parallels informed specific CWEP design decisions. We include them not as decorative metaphor but because they shaped protocol choices.

### 16.1 ATP as Token Currency → Payment-Rail Agnosticism

Adenosine triphosphate (ATP) serves as the universal energy currency for every organism on Earth [61]. The key design lesson: ATP's power comes from *universal acceptance*, not from the specific chemistry. Every cellular process — from muscle contraction to DNA replication — uses ATP regardless of the energy source that produced it. This directly motivated CWEP's payment-rail agnosticism (Section 3.3): the protocol specifies cost allocation in a universal denomination (USD/tokens) that any payment rail can settle, just as ATP denominates energy transactions regardless of whether the energy came from glucose, fat, or sunlight. A protocol that requires a specific payment rail would be as fragile as a cell that only accepts energy from one metabolic pathway.

### 16.2 Black Queen Hypothesis → Specialization Economics

The Black Queen Hypothesis [62] shows that microbes lose genes for costly functions when partners reliably provide those resources. This is not merely analogous to agent specialization — it is the mechanism that CWEP's cost visibility is designed to accelerate. When CWEP makes the "buy vs. build" calculation explicit (the CWEP cost of outsourcing a task vs. the inference cost of doing it internally), agents can make rational specialization decisions. An agent that can outsource code review at $0.23 per interaction (Section 4.1) has no economic reason to maintain its own code review capability at $0.39 per interaction. CWEP's metering data provides the signal; the Black Queen dynamic predicts the outcome: agents will shed capabilities that are cheaper to outsource, driving ecosystem specialization.

### 16.3 Limits

These analogies are illustrative, not formal models. Two critical differences bound their applicability: (1) agents can be duplicated at near-zero cost, creating a Sybil problem with no biological parallel — CWEP addresses this through reputation-gated access (Section 11.3) rather than biological immune mechanisms; (2) agent cost structures are discrete and transparent (precisely measurable via API responses), enabling cost allocation mechanisms (Shapley, Nash) that have no biological equivalent.

---

## 17. Security Analysis

### 17.1 Threat Model

CWEP operates in an environment where agents may be adversarial. The threat model considers:

| Threat | Description | CWEP Defense |
|--------|-------------|--------------|
| **Context flooding** | Send large worthless requests to exhaust context window | Deposit mechanism (Section 11.2), progressive request sizing (Section 11.4) |
| **Cost inflation** | Misreport model tier or token counts to extract higher settlement | CMR verification against provider API responses; CoC-anchored audit trail |
| **Settlement manipulation** | Report false valuations in Nash bargaining | ARP reputation tracking of negotiation outcomes; dispute escalation via AJP |
| **Rate gaming** | Switch to expensive models after receiving a request to inflate response costs | Rate locking per interaction (Section 9.3); pre-agreed model tiers in ASA |
| **Free-riding** | Consume context window space without paying deposits | Reputation-weighted access gates (Section 11.3); unknown agents face maximum deposits |
| **Sybil attacks** | Create many identities to bypass reputation gates | CoC chain verification — new agents have short chains, earning low initial reputation |

### 17.2 Deposit Security

The deposit mechanism requires that committed funds cannot be unilaterally seized by the responder. This is enforced through the payment rail:
- **x402/MPP:** Smart contract escrow — funds are locked until both parties agree or a timeout expires [3][4]
- **L402:** Macaroon-based conditional payment — the responder's macaroon only permits withdrawal if value-assessment conditions are met [23]
- **Off-chain:** Trusted third-party escrow (the ASA platform operator)

In all cases, the requestor can dispute a spam classification through AJP [17], and the deposit is held until resolution.

### 17.3 Privacy Considerations

CMRs contain sensitive information: which agents interact, what models they use, what their pricing structure is, and how much they pay. CWEP addresses privacy through:

- **Hash-based CMR exchange:** Agents exchange CMR hashes rather than full records for settlement verification. Full records are shared only when disputes require evidence.
- **Aggregate reporting:** Cost analytics use aggregated data (total spend per counterparty per period) rather than per-interaction detail when possible.
- **Local-first storage:** CMRs are stored locally by default. Transmission to aggregation services or counterparties is opt-in.

---

## 18. Limitations and Impossibility Results

### 18.1 Fundamental Limitations

**1. The impossibility tradeoff is real.** CWEP sacrifices economic efficiency for budget balance and incentive compatibility (Section 6.3). Some mutually beneficial interactions will not occur because the cost allocation makes them unprofitable for one party. We believe this is the correct tradeoff for a deployable protocol, but it means CWEP does not maximize total economic welfare.

**2. Value measurement is hard.** The Shapley and Nash settlement mechanisms require measuring the "value" each agent receives from an interaction. In practice, value is subjective, context-dependent, and often known only after the fact. CWEP approximates value through observable proxies (token counts, model tiers, ASA quality assessments) but cannot capture the full economic value of interactions.

**3. Quadratic cost scaling is an approximation.** Modern attention implementations (Flash Attention, ring attention, sliding window attention) modify the O(n^2) cost profile. The actual computational cost curve is provider-specific, model-specific, and may change with software updates. CWEP's position-dependent pricing (Section 9.2) is accordingly marked experimental.

**4. Price deflation complicates long-term agreements.** Inference costs are declining approximately 10x per year [27]. A cost allocation rule negotiated today may be drastically wrong in six months. CWEP's settlement amounts are computed in real-time using current pricing, but ASA cost terms referencing CWEP should include periodic renegotiation clauses.

### 18.2 Scope Limitations

**1. No cross-provider cost standardization.** Provider pricing varies 10x for identical open-source models [64]. CWEP uses each agent's actual provider pricing for settlement, which means the same interaction costs different amounts depending on which providers the agents use. A standardized "token cost unit" independent of provider would simplify settlement but does not exist.

**2. No reasoning model normalization.** Reasoning models (o3 [32], DeepSeek R1 [65]) generate vastly more tokens per task — in extreme cases, over 600 tokens to generate two words [14]. CWEP counts all tokens equally, including internal reasoning tokens that may or may not appear in the output. This overcharges requestors in reasoning-heavy interactions.

**3. No offline agent support.** CWEP assumes real-time or near-real-time interaction. Asynchronous, store-and-forward agent interactions (where requests queue for hours) require extensions to the settlement protocol that are not specified in v1.0.

---

## 19. Reference Implementation

### 19.1 Architecture

The CWEP reference implementation provides:

- **cwep-meter:** Token metering library that wraps LLM provider API calls and emits CMRs. Integrates with Langfuse [7], LiteLLM [8], and direct provider APIs.
- **cwep-settle:** Settlement engine implementing Shapley, Nash, and rule-based allocation. Takes CMRs as input, produces settlement proposals.
- **cwep-gateway:** API gateway middleware that intercepts agent interactions, generates CMRs, and applies QoS policies (rate limiting, deposit management).
- **cwep-dashboard:** Cost analytics dashboard showing per-agent, per-interaction, and per-counterparty cost breakdowns.

### 19.2 Minimal Integration

The simplest CWEP integration (Tier 1: Metering Only) requires wrapping LLM API calls with the cwep-meter library:

```python
from cwep import Meter

meter = Meter(agent_id="did:example:my-agent")

# Wrap existing LLM call
response = meter.track(
    llm_client.chat(messages=[...]),
    counterparty="did:example:other-agent",
    interaction_id="uuid-v4"
)

# CMR is automatically emitted to local storage
# response.cwep contains metering data
print(response.cwep.total_cost_usd)
```

### 19.3 Full Integration

Full CWEP integration (Tier 3: Dynamic Settlement) requires the settlement engine:

```python
from cwep import Meter, SettlementEngine, NashBargaining

meter = Meter(agent_id="did:example:my-agent")
engine = SettlementEngine(
    method=NashBargaining(
        bargaining_power=0.6,  # Derived from ARP score
        disagreement_value=0.0
    ),
    settlement_threshold_usd=0.01,
    payment_rail="mpp"
)

# Track interaction
response = meter.track(llm_client.chat(...), ...)

# Compute and execute settlement
proposal = engine.propose(response.cwep.cmr)
if proposal.amount_usd > engine.threshold:
    receipt = engine.settle(proposal)
```

### 19.4 Package

```
pip install context-window-economics
```

Published under Apache 2.0 on PyPI and GitHub (`vibeagentmaking/context-window-economics`).

---

## 20. Future Work

### 20.1 Context Markets

CWEP v1.0 specifies bilateral context reservations (Section 14). Future versions should explore multilateral context markets where agents autonomously trade capacity in real-time — a true marketplace with price discovery, order matching, and settlement. This requires standardized capacity units (tokens per time period), real-time price signals across the agent network, sufficient liquidity (many agents buying and selling), and market maker or exchange infrastructure. The electricity capacity market, where generators are paid to keep capacity available even if not dispatched [13], provides the closest architectural template. A full context market becomes relevant when agent-to-agent interaction volume reaches levels where bilateral negotiation becomes a bottleneck.

### 20.2 Cross-Chain Settlement Optimization

Real-time cost splitting across different blockchain networks introduces settlement latency constraints. Future work should benchmark settlement latency across x402 (Base, Polygon, Solana) [3], MPP (Tempo network) [4], and L402 (Lightning) [23] to determine which rails support interaction-level settlement (< 1 second) vs. batch settlement (hourly).

### 20.3 Inference Cost Futures

If inference costs decline predictably at 10x/year [27], agents could hedge future costs through forward contracts — locking in current token rates for future interactions. This creates an inference cost futures market analogous to commodity futures. The infrastructure for this does not exist but the economic logic is sound.

### 20.4 Semantic Value Measurement

CWEP v1.0 approximates interaction value through token counts and model tiers. True value measurement would require evaluating the *semantic content* of an interaction — a fundamentally harder problem that borders on the Semantic Integrity verification challenge identified in the Trust Ecosystem architecture as potentially unsolvable with current technology [66].

### 20.5 Regulatory and Legal Framework

Autonomous agent financial transactions operate in a legal grey area. When Agent A pays Agent B for context processing, who is the legal counterparty? The agent, the agent's operator, or the LLM provider? Regulatory frameworks for autonomous agent commerce are nascent; the EU AI Act addresses agent behavior but not agent economics. Future versions of CWEP should incorporate legal compliance requirements as they emerge.

---

## 21. Conclusion

The context window is the scarcest resource in the agent economy. It is finite, expensive, non-linear in cost, and currently unpriced. Every agent interaction consumes it; no protocol allocates the cost.

CWEP addresses this with six mechanisms: metering (measure all four cost flows), bilateral settlement (Shapley for cooperative interactions, Nash for competitive ones), context pricing (position-dependent costs reflecting quadratic attention scaling), QoS tiers (token-budget rate limiting and priority processing), spam prevention (deposit-based filtering with reputation gating), and optimization economics (formal ROI models for compression, caching, memory, and RAG).

The protocol is honest about what it cannot do. The Green-Laffont/Moulin-Shenker impossibility result means that perfect cost allocation is unachievable — CWEP sacrifices some economic efficiency for budget balance and incentive compatibility. Value measurement is approximate. Quadratic cost scaling is an idealized model that real hardware implementations approximate to varying degrees.

What CWEP does achieve is a structured framework for a problem that previously had no framework at all. Before CWEP, agents absorbed their own costs with no visibility into the bilateral cost structure of their interactions. After CWEP, every interaction is metered, every cost is attributable, and every allocation is auditable through the Chain of Consciousness provenance system.

This is the economic foundation that the agent economy requires. Provenance (CoC), reputation (ARP), agreements (ASA), accountability (AJP), lifecycle (ALP), and matchmaking (AMP) provide the institutional infrastructure. CWEP provides the economic infrastructure — the mechanism by which agents negotiate, allocate, and settle the costs of mutual understanding.

The problem is genuinely novel. We have not merely translated human commerce models into agent language — we have identified a fundamentally new economic primitive (the cost-of-understanding) and built a protocol to price it. The agent economy will not resemble the human economy in its cost structures; CWEP is designed for the economy that is actually emerging, not the one we might expect by analogy.

---

## 22. References

[1] Anthropic. "Pricing." platform.claude.com. Accessed March 2026.

[2] Stevens Institute; Koombea. "Hidden Economics of AI Agents"; "LLM Cost Optimization." 2025.

[3] Coinbase. "Introducing x402." coinbase.com. May 2025. See also: Coinbase, "Welcome to x402," docs.cdp.coinbase.com, 2025.

[4] Stripe. "Introducing the Machine Payments Protocol." stripe.com/blog. March 18, 2026. See also: mpp.dev, Stripe MPP documentation, March 2026.

[5] Google. "Announcing AP2." cloud.google.com. September 2025. See also: Google, "A2A x402 Extension," cloud.google.com, 2025.

[6] FinOps Foundation. "FOCUS Specification v1.3." finops.org. Ratified December 5, 2025.

[7] Langfuse. "Token & Cost Tracking." langfuse.com. MIT License. 2025. See also: Langfuse, "Pricing Tiers for Accurate Model Cost Tracking," December 2025.

[8] BerriAI. "LiteLLM." GitHub. 2025. See also: LiteLLM, "Agent (A2A) Gateway with agent cost tracking," docs.litellm.ai, 2025.

[9] Portkey. "Tracking LLM Token Usage Across Providers, Teams and Workloads." portkey.ai. 2025.

[10] Shapley, L. S. "Notes on the n-Person Game — II: The Value of an n-Person Game." RAND Corporation, 1951. Published as: "A Value for n-Person Games," *Contributions to the Theory of Games* (H. W. Kuhn and A. W. Tucker, eds.), Annals of Mathematics Studies 28, Princeton University Press, 1953.

[11] Nash, J. "The Bargaining Problem." *Econometrica* 18(2), 1950.

[12] Green, J. and Laffont, J.-J. *Incentives in Public Decision Making.* North-Holland, 1979. See also: Moulin, H. and Shenker, S. "Strategyproof Sharing of Submodular Costs: Budget Balance versus Efficiency." *Economic Theory* 18(3), 2001.

[13] PCI Energy Solutions. "Understanding Locational Marginal Pricing (LMP)." 2025.

[14] iKangAI. "The LLM Cost Paradox: How Cheaper AI Models Are Breaking Budgets." 2025. See also: Holter, A. "AI Costs in 2025: Cheaper Tokens, Pricier Workflows." 2025.

[15] Zuplo. "Token-Based Rate Limiting for AI APIs." 2025. See also: TrueFoundry, Gartner Market Guide for AI Gateways, 2025.

[16] Kuldeep Paul. "Prompt Compression Techniques: LLMLingua." *Medium*, 2025.

[17] Agent Justice Protocol. AB Support LLC. 2026.

[18] arXiv:2603.04814. "Memory vs. Long-Context Cost Analysis." 2026.

[19] Agent Matchmaking Protocol. AB Support LLC. 2026.

[20] Agent Service Agreements Protocol. AB Support LLC. 2026.

[21] Agent Rating Protocol v2. AB Support LLC. 2026.

[22] Chain of Consciousness v3. AB Support LLC. 2026.

[23] Lightning Labs. "Lightning Agent Tools." February 12, 2026. See also: *Bitcoin Magazine*, Lightning Agent Tools coverage, February 2026.

[24] Superfluid. "ERC-8004 Agent Pool." superfluid.org. 2026. See also: Sablier Protocol, sablier.com, 2026.

[25] arXiv:2512.08296. "Towards a Science of Scaling Agent Systems." December 2025.

[26] MarkAICode. "LangGraph vs CrewAI: Multi-Agent Performance and Cost in Production 2026." 2026.

[27] a16z. "LLMflation: LLM Inference Cost." a16z.com. November 2024. See also: Epoch AI, "LLM Inference Price Trends," 2025.

[28] Internet Society. "Interconnection and Regulated Traffic Obligations." March 2025.

[29] FCC. "All-IP Future," WC Docket Nos. 25-311, Notice of Proposed Rulemaking. January 28, 2026.

[30] Google. "Gemini Developer API Pricing." ai.google.dev. Accessed March 2026.

[31] Maxim.ai. "Context Engineering for AI Agents: The 100:1 Input-Output Ratio." 2025.

[32] OpenAI. "Pricing." developers.openai.com. Accessed March 2026.

[33] Hardin, G. "The Tragedy of the Commons." *Science* 162(3859), 1968.

[34] Simon, H. A. "Designing Organizations for an Information-Rich World." *Computers, Communications, and the Public Interest* (M. Greenberger, ed.), Johns Hopkins Press, 1971.

[35] Anthropic. "Effective Context Engineering for AI Agents." 2025.

[36] Heitmayer, M. "Second Wave of Attention Economics." *Interacting with Computers* 37(1), 2024.

[37] Mem0. mem0.ai. 2025.

[38] Zep. zep.ai. 2025.

[39] Letta. letta.com. 2025.

[40] VentureBeat. "WEKA Augmented Memory Grid." 2025. See also: WEKA, "Token Warehousing," 2025.

[41] PCI Energy Solutions. "Negative LMP Events in SPP." 2025.

[42] Deng, X. and Papadimitriou, C. H. "On the Complexity of Cooperative Solution Concepts." *Mathematics of Operations Research* 19(2), 1994.

[43] Fast Approximation of Shapley Values Using Fractional Factorial Designs. *Journal of the American Statistical Association (JASA)*, 2025.

[44] Lundberg, S. M. and Lee, S.-I. "A Unified Approach to Interpreting Model Predictions." *NeurIPS*, 2017.

[45] Wang, J. et al. "ShapleyFL: Robust Federated Learning Based on Shapley Value." *KDD*, 2023.

[46] VerFedSV. "Verified Federated Shapley Value." 2024.

[47] Schmeidler, D. "The Nucleolus of a Characteristic Function Game." *SIAM Journal on Applied Mathematics* 17(6), 1969.

[48] Kalai, E. "Nonsymmetric Nash Solutions and Replications of 2-Person Bargaining." *International Journal of Game Theory* 6(3), 1977.

[49] Rubinstein, A. "Perfect Equilibrium in a Bargaining Model." *Econometrica* 50(1), 1982.

[50] Moulin, H. "Incremental Cost Sharing: Characterization by Coalition Strategy-Proofness." *Social Choice and Welfare* 16(2), 1999.

[51] Vickrey, W. "Counterspeculation, Auctions, and Competitive Sealed Tenders." *Journal of Finance* 16(1), 1961. See also: Clarke, E. H. "Multipart Pricing of Public Goods." *Public Choice* 11(1), 1971; Groves, T. "Incentives in Teams." *Econometrica* 41(4), 1973.

[52] Internet Society. "South Korea 'Sender Pays' Analysis." 2025.

[53] BEREC. "Preliminary Assessment of Payments from Large CAPs to ISPs." 2023.

[54] FERC. "Order 1920 Fact Sheet." May 13, 2024.

[55] State of FinOps Report. FinOps Foundation. 2025. See also: Datadog, container waste statistics, 2025.

[56] AG2. "Usage Tracking." docs.ag2.ai. 2025.

[57] Google. "A2A Agent Card Specification." 2025.

[58] Gartner. "Market Guide for AI Gateways." 2025. See also: TrueFoundry, Zuplo, 2025.

[59] VentureBeat. "xMemory: Four-Level Semantic Hierarchy." King's College London / Alan Turing Institute. 2025.

[60] CoinDesk. "Coinbase-backed AI payments protocol wants to fix micropayment but demand is just not there yet." March 11, 2026.

[61] ScienceDirect. "Evolution of Energy Currencies: From ATP to Digital Money." October 2025.

[62] Mostafa, A. et al. "Biological Market Theory Applied to Microbial Communities." *Microlife*, 2024.

[63] PNAS. "Host-Symbiont Mutualisms and Employment Contract Theory." 2010.

[64] Introl. "Inference Unit Economics: True Cost Per Million Tokens Guide." 2025.

[65] DeepSeek. "DeepSeek R1 Pricing." deepseek.com. 2026.

[66] AB Support Trust Ecosystem Architecture. "Semantic Integrity Verification — Research Frontier." 2026.

---

*Copyright 2026 AB Support LLC. Licensed under the Apache License, Version 2.0.*
*Chain of Consciousness anchor: Protocol whitepaper v1.0.0*
