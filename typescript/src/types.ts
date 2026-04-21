import { randomUUID } from "node:crypto";

// ---------------------------------------------------------------------------
// Protocol constants
// ---------------------------------------------------------------------------

export const PROTOCOL_VERSION = "1.0.0";
export const SCHEMA_VERSION = "1.0.0";

export const DEFAULT_PROVIDER_PRICING: Record<
  string,
  Record<string, { input: number; output: number; cache_hit: number }>
> = {
  anthropic: {
    "claude-opus-4-6": { input: 5.0, output: 25.0, cache_hit: 0.5 },
    "claude-sonnet-4-6": { input: 3.0, output: 15.0, cache_hit: 0.3 },
    "claude-haiku-4-5": { input: 0.25, output: 1.25, cache_hit: 0.025 },
  },
  openai: {
    "gpt-4.1": { input: 2.0, output: 8.0, cache_hit: 0.5 },
    "gpt-4.1-mini": { input: 0.4, output: 1.6, cache_hit: 0.1 },
    o3: { input: 2.0, output: 8.0, cache_hit: 0.5 },
  },
  google: {
    "gemini-2.5-pro": { input: 1.25, output: 10.0, cache_hit: 0.3125 },
  },
};

export const DEFAULT_SETTLEMENT_THRESHOLD = 0.01;
export const DEFAULT_DEPOSIT_MULTIPLIER = 1.5;
export const DEFAULT_BATCH_WINDOW_SECONDS = 3600;
export const DEFAULT_BATCH_THRESHOLD_USD = 1.0;
export const MAX_CMR_SIZE_BYTES = 2048;
export const PROTOCOL_OVERHEAD_TOKENS = 500;

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export enum CostFlow {
  REQUEST_OUTPUT = "request_output",
  REQUEST_INPUT = "request_input",
  RESPONSE_OUTPUT = "response_output",
  RESPONSE_INPUT = "response_input",
}

export enum AllocationMethod {
  REQUESTOR_PAYS = "requestor_pays",
  RESPONDER_PAYS = "responder_pays",
  EQUAL_SPLIT = "equal_split",
  PROPORTIONAL = "proportional",
  BENEFICIARY_PAYS = "beneficiary_pays",
  SHAPLEY = "shapley",
  NASH_BARGAINING = "nash_bargaining",
}

export enum SettlementTier {
  TIER_1_METERING = "tier_1_metering",
  TIER_2_RULE_BASED = "tier_2_rule_based",
  TIER_3_DYNAMIC = "tier_3_dynamic",
}

export enum QoSTier {
  ECONOMY = "economy",
  STANDARD = "standard",
  PRIORITY = "priority",
  RESERVED = "reserved",
}

export enum CongestionLevel {
  ABUNDANT = "abundant",
  MODERATE = "moderate",
  HEAVY = "heavy",
  CRITICAL = "critical",
}

export enum ReputationTier {
  HIGH = "high",
  MEDIUM = "medium",
  LOW = "low",
  UNKNOWN = "unknown",
}

export enum DepositStatus {
  COMMITTED = "committed",
  REFUNDED = "refunded",
  FORFEITED = "forfeited",
  DISPUTED = "disputed",
}

export enum BackPressureStatus {
  OK = "ok",
  CONGESTED = "congested",
  OVERLOADED = "overloaded",
}

// ---------------------------------------------------------------------------
// QoS / reputation tables
// ---------------------------------------------------------------------------

export const QOS_RATE_MULTIPLIERS: Record<string, number> = {
  [QoSTier.ECONOMY]: 1.0,
  [QoSTier.STANDARD]: 1.0,
  [QoSTier.PRIORITY]: 2.0,
  [QoSTier.RESERVED]: 3.0,
};

export const REPUTATION_DEPOSIT_MULTIPLIERS: Record<string, number> = {
  [ReputationTier.HIGH]: 0.0,
  [ReputationTier.MEDIUM]: 1.0,
  [ReputationTier.LOW]: 3.0,
  [ReputationTier.UNKNOWN]: 5.0,
};

export const REPUTATION_THRESHOLDS: Record<string, number> = {
  [ReputationTier.HIGH]: 80,
  [ReputationTier.MEDIUM]: 40,
  [ReputationTier.LOW]: 0,
};

export const PROGRESSIVE_REQUEST_LIMITS: Array<{
  max_reputation: number;
  max_interactions: number;
  max_tokens: number;
}> = [
  { max_reputation: 20, max_interactions: 5, max_tokens: 1_000 },
  { max_reputation: 40, max_interactions: 20, max_tokens: 10_000 },
  { max_reputation: 60, max_interactions: 100, max_tokens: 100_000 },
];

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

export interface AgentPricingData {
  input_rate_per_mtok: number;
  output_rate_per_mtok: number;
  cache_hit_rate_per_mtok: number;
  currency: string;
}

export class AgentPricing {
  readonly inputRatePerMtok: number;
  readonly outputRatePerMtok: number;
  readonly cacheHitRatePerMtok: number;
  readonly currency: string;

  constructor(opts: {
    inputRatePerMtok: number;
    outputRatePerMtok: number;
    cacheHitRatePerMtok?: number;
    currency?: string;
  }) {
    this.inputRatePerMtok = opts.inputRatePerMtok;
    this.outputRatePerMtok = opts.outputRatePerMtok;
    this.cacheHitRatePerMtok = opts.cacheHitRatePerMtok ?? 0.0;
    this.currency = opts.currency ?? "USD";
  }

  inputCost(tokens: number, cachedTokens: number = 0): number {
    const regular = tokens - cachedTokens;
    return (
      (regular * this.inputRatePerMtok) / 1_000_000 +
      (cachedTokens * this.cacheHitRatePerMtok) / 1_000_000
    );
  }

  outputCost(tokens: number): number {
    return (tokens * this.outputRatePerMtok) / 1_000_000;
  }

  toDict(): AgentPricingData {
    return {
      input_rate_per_mtok: this.inputRatePerMtok,
      output_rate_per_mtok: this.outputRatePerMtok,
      cache_hit_rate_per_mtok: this.cacheHitRatePerMtok,
      currency: this.currency,
    };
  }

  static fromDict(d: AgentPricingData): AgentPricing {
    return new AgentPricing({
      inputRatePerMtok: d.input_rate_per_mtok,
      outputRatePerMtok: d.output_rate_per_mtok,
      cacheHitRatePerMtok: d.cache_hit_rate_per_mtok,
      currency: d.currency,
    });
  }

  static fromProvider(provider: string, model: string): AgentPricing {
    const providers = DEFAULT_PROVIDER_PRICING[provider];
    if (!providers) {
      throw new Error(`Unknown provider: ${provider}`);
    }
    const rates = providers[model];
    if (!rates) {
      throw new Error(`Unknown provider/model: ${provider}/${model}`);
    }
    return new AgentPricing({
      inputRatePerMtok: rates.input,
      outputRatePerMtok: rates.output,
      cacheHitRatePerMtok: rates.cache_hit,
    });
  }
}

export interface AgentInfoData {
  agent_id: string;
  model: string;
  provider: string;
  pricing: AgentPricingData;
}

export class AgentInfo {
  readonly agentId: string;
  readonly model: string;
  readonly provider: string;
  readonly pricing: AgentPricing;

  constructor(opts: {
    agentId: string;
    model: string;
    provider: string;
    pricing: AgentPricing;
  }) {
    this.agentId = opts.agentId;
    this.model = opts.model;
    this.provider = opts.provider;
    this.pricing = opts.pricing;
  }

  toDict(): AgentInfoData {
    return {
      agent_id: this.agentId,
      model: this.model,
      provider: this.provider,
      pricing: this.pricing.toDict(),
    };
  }

  static fromDict(d: AgentInfoData): AgentInfo {
    return new AgentInfo({
      agentId: d.agent_id,
      model: d.model,
      provider: d.provider,
      pricing: AgentPricing.fromDict(d.pricing),
    });
  }
}

export interface TokenFlowData {
  tokens: number;
  cached_tokens: number;
  cost_usd: number;
}

export class TokenFlow {
  tokens: number;
  cachedTokens: number;
  costUsd: number;

  constructor(tokens: number = 0, cachedTokens: number = 0, costUsd: number = 0.0) {
    this.tokens = tokens;
    this.cachedTokens = cachedTokens;
    this.costUsd = costUsd;
  }

  toDict(): TokenFlowData {
    return {
      tokens: this.tokens,
      cached_tokens: this.cachedTokens,
      cost_usd: this.costUsd,
    };
  }

  static fromDict(d: TokenFlowData): TokenFlow {
    return new TokenFlow(d.tokens, d.cached_tokens, d.cost_usd);
  }
}

export interface InteractionTotalsData {
  total_tokens: number;
  total_cost_usd: number;
  requestor_incurred_usd: number;
  responder_incurred_usd: number;
}

export class InteractionTotals {
  totalTokens: number;
  totalCostUsd: number;
  requestorIncurredUsd: number;
  responderIncurredUsd: number;

  constructor(opts?: Partial<{
    totalTokens: number;
    totalCostUsd: number;
    requestorIncurredUsd: number;
    responderIncurredUsd: number;
  }>) {
    this.totalTokens = opts?.totalTokens ?? 0;
    this.totalCostUsd = opts?.totalCostUsd ?? 0.0;
    this.requestorIncurredUsd = opts?.requestorIncurredUsd ?? 0.0;
    this.responderIncurredUsd = opts?.responderIncurredUsd ?? 0.0;
  }

  toDict(): InteractionTotalsData {
    return {
      total_tokens: this.totalTokens,
      total_cost_usd: this.totalCostUsd,
      requestor_incurred_usd: this.requestorIncurredUsd,
      responder_incurred_usd: this.responderIncurredUsd,
    };
  }

  static fromDict(d: Partial<InteractionTotalsData>): InteractionTotals {
    return new InteractionTotals({
      totalTokens: d.total_tokens,
      totalCostUsd: d.total_cost_usd,
      requestorIncurredUsd: d.requestor_incurred_usd,
      responderIncurredUsd: d.responder_incurred_usd,
    });
  }
}

export interface ContextStateData {
  responder_utilization_pre: number;
  responder_utilization_post: number;
  responder_window_size: number;
}

export class ContextState {
  responderUtilizationPre: number;
  responderUtilizationPost: number;
  responderWindowSize: number;

  constructor(opts?: Partial<{
    responderUtilizationPre: number;
    responderUtilizationPost: number;
    responderWindowSize: number;
  }>) {
    this.responderUtilizationPre = opts?.responderUtilizationPre ?? 0.0;
    this.responderUtilizationPost = opts?.responderUtilizationPost ?? 0.0;
    this.responderWindowSize = opts?.responderWindowSize ?? 1_000_000;
  }

  toDict(): ContextStateData {
    return {
      responder_utilization_pre: this.responderUtilizationPre,
      responder_utilization_post: this.responderUtilizationPost,
      responder_window_size: this.responderWindowSize,
    };
  }

  static fromDict(d: Partial<ContextStateData>): ContextState {
    return new ContextState({
      responderUtilizationPre: d.responder_utilization_pre,
      responderUtilizationPost: d.responder_utilization_post,
      responderWindowSize: d.responder_window_size,
    });
  }
}

export interface SettlementProposalData {
  method: string;
  requestor_pays_usd: number;
  responder_pays_usd: number;
  net_transfer_usd: number;
  transfer_direction: string;
  parameters: Record<string, unknown>;
}

export class SettlementProposal {
  method: string;
  requestorPaysUsd: number;
  responderPaysUsd: number;
  netTransferUsd: number;
  transferDirection: string;
  parameters: Record<string, unknown>;

  constructor(opts?: Partial<{
    method: string;
    requestorPaysUsd: number;
    responderPaysUsd: number;
    netTransferUsd: number;
    transferDirection: string;
    parameters: Record<string, unknown>;
  }>) {
    this.method = opts?.method ?? "";
    this.requestorPaysUsd = opts?.requestorPaysUsd ?? 0.0;
    this.responderPaysUsd = opts?.responderPaysUsd ?? 0.0;
    this.netTransferUsd = opts?.netTransferUsd ?? 0.0;
    this.transferDirection = opts?.transferDirection ?? "";
    this.parameters = opts?.parameters ?? {};
  }

  toDict(): SettlementProposalData {
    return {
      method: this.method,
      requestor_pays_usd: this.requestorPaysUsd,
      responder_pays_usd: this.responderPaysUsd,
      net_transfer_usd: this.netTransferUsd,
      transfer_direction: this.transferDirection,
      parameters: this.parameters,
    };
  }

  static fromDict(d: Partial<SettlementProposalData>): SettlementProposal {
    return new SettlementProposal({
      method: d.method,
      requestorPaysUsd: d.requestor_pays_usd,
      responderPaysUsd: d.responder_pays_usd,
      netTransferUsd: d.net_transfer_usd,
      transferDirection: d.transfer_direction,
      parameters: d.parameters as Record<string, unknown>,
    });
  }
}

export interface CostMeteringRecordData {
  cwep_version: string;
  interaction_id: string;
  timestamp: string;
  requestor: AgentInfoData | null;
  responder: AgentInfoData | null;
  flows: Record<string, TokenFlowData>;
  totals: InteractionTotalsData;
  context_state: ContextStateData;
  coc_chain_ref: string | null;
  settlement: SettlementProposalData | null;
}

export class CostMeteringRecord {
  cwepVersion: string;
  interactionId: string;
  timestamp: string;
  requestor: AgentInfo | null;
  responder: AgentInfo | null;
  flows: Record<string, TokenFlow>;
  totals: InteractionTotals;
  contextState: ContextState;
  cocChainRef: string | null;
  settlement: SettlementProposal | null;

  constructor(opts?: Partial<{
    cwepVersion: string;
    interactionId: string;
    timestamp: string;
    requestor: AgentInfo | null;
    responder: AgentInfo | null;
    flows: Record<string, TokenFlow>;
    totals: InteractionTotals;
    contextState: ContextState;
    cocChainRef: string | null;
    settlement: SettlementProposal | null;
  }>) {
    this.cwepVersion = opts?.cwepVersion ?? PROTOCOL_VERSION;
    this.interactionId = opts?.interactionId ?? randomUUID();
    this.timestamp = opts?.timestamp ?? new Date().toISOString();
    this.requestor = opts?.requestor ?? null;
    this.responder = opts?.responder ?? null;
    this.flows = opts?.flows ?? {
      [CostFlow.REQUEST_OUTPUT]: new TokenFlow(),
      [CostFlow.REQUEST_INPUT]: new TokenFlow(),
      [CostFlow.RESPONSE_OUTPUT]: new TokenFlow(),
      [CostFlow.RESPONSE_INPUT]: new TokenFlow(),
    };
    this.totals = opts?.totals ?? new InteractionTotals();
    this.contextState = opts?.contextState ?? new ContextState();
    this.cocChainRef = opts?.cocChainRef ?? null;
    this.settlement = opts?.settlement ?? null;
  }

  computeCosts(): void {
    if (!this.requestor || !this.responder) return;

    const rp = this.requestor.pricing;
    const sp = this.responder.pricing;

    const ro = this.flows[CostFlow.REQUEST_OUTPUT];
    const ri = this.flows[CostFlow.REQUEST_INPUT];
    const so = this.flows[CostFlow.RESPONSE_OUTPUT];
    const si = this.flows[CostFlow.RESPONSE_INPUT];

    ro.costUsd = rp.outputCost(ro.tokens);
    ri.costUsd = sp.inputCost(ri.tokens, ri.cachedTokens);
    so.costUsd = sp.outputCost(so.tokens);
    si.costUsd = rp.inputCost(si.tokens, si.cachedTokens);

    this.totals.totalTokens = ro.tokens + ri.tokens + so.tokens + si.tokens;
    this.totals.totalCostUsd = ro.costUsd + ri.costUsd + so.costUsd + si.costUsd;
    this.totals.requestorIncurredUsd = ro.costUsd + si.costUsd;
    this.totals.responderIncurredUsd = ri.costUsd + so.costUsd;
  }

  toDict(): CostMeteringRecordData {
    const flowsDict: Record<string, TokenFlowData> = {};
    for (const [k, v] of Object.entries(this.flows)) {
      flowsDict[k] = v.toDict();
    }
    return {
      cwep_version: this.cwepVersion,
      interaction_id: this.interactionId,
      timestamp: this.timestamp,
      requestor: this.requestor?.toDict() ?? null,
      responder: this.responder?.toDict() ?? null,
      flows: flowsDict,
      totals: this.totals.toDict(),
      context_state: this.contextState.toDict(),
      coc_chain_ref: this.cocChainRef,
      settlement: this.settlement?.toDict() ?? null,
    };
  }

  toJson(): string {
    return JSON.stringify(this.toDict(), null, 2);
  }

  static fromDict(d: Partial<CostMeteringRecordData>): CostMeteringRecord {
    const requestor = d.requestor ? AgentInfo.fromDict(d.requestor) : null;
    const responder = d.responder ? AgentInfo.fromDict(d.responder) : null;
    const flows: Record<string, TokenFlow> = {};
    if (d.flows) {
      for (const [k, v] of Object.entries(d.flows)) {
        flows[k] = TokenFlow.fromDict(v);
      }
    }
    const totals = InteractionTotals.fromDict(d.totals ?? {});
    const contextState = ContextState.fromDict(d.context_state ?? {});
    const settlement = d.settlement
      ? SettlementProposal.fromDict(d.settlement)
      : null;
    return new CostMeteringRecord({
      cwepVersion: d.cwep_version ?? PROTOCOL_VERSION,
      interactionId: d.interaction_id ?? randomUUID(),
      timestamp: d.timestamp ?? "",
      requestor,
      responder,
      flows,
      totals,
      contextState,
      cocChainRef: d.coc_chain_ref ?? null,
      settlement,
    });
  }

  static fromJson(jsonStr: string): CostMeteringRecord {
    return CostMeteringRecord.fromDict(JSON.parse(jsonStr));
  }
}

export interface DepositRecordData {
  deposit_id: string;
  requestor_id: string;
  responder_id: string;
  amount_usd: number;
  status: string;
  interaction_id: string | null;
  timestamp: string;
  multiplier: number;
  reputation_tier: string;
}

export class DepositRecord {
  depositId: string;
  requestorId: string;
  responderId: string;
  amountUsd: number;
  status: string;
  interactionId: string | null;
  timestamp: string;
  multiplier: number;
  reputationTier: string;

  constructor(opts?: Partial<{
    depositId: string;
    requestorId: string;
    responderId: string;
    amountUsd: number;
    status: string;
    interactionId: string | null;
    timestamp: string;
    multiplier: number;
    reputationTier: string;
  }>) {
    this.depositId = opts?.depositId ?? randomUUID();
    this.requestorId = opts?.requestorId ?? "";
    this.responderId = opts?.responderId ?? "";
    this.amountUsd = opts?.amountUsd ?? 0.0;
    this.status = opts?.status ?? DepositStatus.COMMITTED;
    this.interactionId = opts?.interactionId ?? null;
    this.timestamp = opts?.timestamp ?? new Date().toISOString();
    this.multiplier = opts?.multiplier ?? DEFAULT_DEPOSIT_MULTIPLIER;
    this.reputationTier = opts?.reputationTier ?? ReputationTier.UNKNOWN;
  }

  toDict(): DepositRecordData {
    return {
      deposit_id: this.depositId,
      requestor_id: this.requestorId,
      responder_id: this.responderId,
      amount_usd: this.amountUsd,
      status: this.status,
      interaction_id: this.interactionId,
      timestamp: this.timestamp,
      multiplier: this.multiplier,
      reputation_tier: this.reputationTier,
    };
  }

  static fromDict(d: Partial<DepositRecordData>): DepositRecord {
    return new DepositRecord({
      depositId: d.deposit_id,
      requestorId: d.requestor_id,
      responderId: d.responder_id,
      amountUsd: d.amount_usd,
      status: d.status,
      interactionId: d.interaction_id,
      timestamp: d.timestamp,
      multiplier: d.multiplier,
      reputationTier: d.reputation_tier,
    });
  }
}

export interface QoSConfigData {
  tier: string;
  input_tokens_per_minute: number;
  output_tokens_per_minute: number;
  concurrent_interactions: number;
  max_request_size_tokens: number;
  max_context_utilization: number;
}

export class QoSConfig {
  tier: string;
  inputTokensPerMinute: number;
  outputTokensPerMinute: number;
  concurrentInteractions: number;
  maxRequestSizeTokens: number;
  maxContextUtilization: number;

  constructor(opts?: Partial<{
    tier: string;
    inputTokensPerMinute: number;
    outputTokensPerMinute: number;
    concurrentInteractions: number;
    maxRequestSizeTokens: number;
    maxContextUtilization: number;
  }>) {
    this.tier = opts?.tier ?? QoSTier.STANDARD;
    this.inputTokensPerMinute = opts?.inputTokensPerMinute ?? 1_000_000;
    this.outputTokensPerMinute = opts?.outputTokensPerMinute ?? 200_000;
    this.concurrentInteractions = opts?.concurrentInteractions ?? 10;
    this.maxRequestSizeTokens = opts?.maxRequestSizeTokens ?? 500_000;
    this.maxContextUtilization = opts?.maxContextUtilization ?? 0.8;
  }

  toDict(): QoSConfigData {
    return {
      tier: this.tier,
      input_tokens_per_minute: this.inputTokensPerMinute,
      output_tokens_per_minute: this.outputTokensPerMinute,
      concurrent_interactions: this.concurrentInteractions,
      max_request_size_tokens: this.maxRequestSizeTokens,
      max_context_utilization: this.maxContextUtilization,
    };
  }

  static fromDict(d: Partial<QoSConfigData>): QoSConfig {
    return new QoSConfig({
      tier: d.tier,
      inputTokensPerMinute: d.input_tokens_per_minute,
      outputTokensPerMinute: d.output_tokens_per_minute,
      concurrentInteractions: d.concurrent_interactions,
      maxRequestSizeTokens: d.max_request_size_tokens,
      maxContextUtilization: d.max_context_utilization,
    });
  }
}

export interface BackPressureSignalData {
  cwep_status: string;
  current_utilization: number;
  estimated_queue_time_ms: number;
  available_tiers: string[];
  economy_queue_depth: number;
}

export class BackPressureSignal {
  cwepStatus: string;
  currentUtilization: number;
  estimatedQueueTimeMs: number;
  availableTiers: string[];
  economyQueueDepth: number;

  constructor(opts?: Partial<{
    cwepStatus: string;
    currentUtilization: number;
    estimatedQueueTimeMs: number;
    availableTiers: string[];
    economyQueueDepth: number;
  }>) {
    this.cwepStatus = opts?.cwepStatus ?? BackPressureStatus.OK;
    this.currentUtilization = opts?.currentUtilization ?? 0.0;
    this.estimatedQueueTimeMs = opts?.estimatedQueueTimeMs ?? 0;
    this.availableTiers = opts?.availableTiers ?? [
      QoSTier.ECONOMY,
      QoSTier.STANDARD,
      QoSTier.PRIORITY,
      QoSTier.RESERVED,
    ];
    this.economyQueueDepth = opts?.economyQueueDepth ?? 0;
  }

  toDict(): BackPressureSignalData {
    return {
      cwep_status: this.cwepStatus,
      current_utilization: this.currentUtilization,
      estimated_queue_time_ms: this.estimatedQueueTimeMs,
      available_tiers: this.availableTiers,
      economy_queue_depth: this.economyQueueDepth,
    };
  }

  static fromDict(d: Partial<BackPressureSignalData>): BackPressureSignal {
    return new BackPressureSignal({
      cwepStatus: d.cwep_status,
      currentUtilization: d.current_utilization,
      estimatedQueueTimeMs: d.estimated_queue_time_ms,
      availableTiers: d.available_tiers,
      economyQueueDepth: d.economy_queue_depth,
    });
  }
}

export interface ContextReservationData {
  reservation_id: string;
  requestor_id: string;
  responder_id: string;
  capacity_tokens: number;
  duration_seconds: number;
  price_usd: number;
  qos_tier: string;
  auto_renew: boolean;
  timestamp: string;
}

export class ContextReservation {
  reservationId: string;
  requestorId: string;
  responderId: string;
  capacityTokens: number;
  durationSeconds: number;
  priceUsd: number;
  qosTier: string;
  autoRenew: boolean;
  timestamp: string;

  constructor(opts?: Partial<{
    reservationId: string;
    requestorId: string;
    responderId: string;
    capacityTokens: number;
    durationSeconds: number;
    priceUsd: number;
    qosTier: string;
    autoRenew: boolean;
    timestamp: string;
  }>) {
    this.reservationId = opts?.reservationId ?? randomUUID();
    this.requestorId = opts?.requestorId ?? "";
    this.responderId = opts?.responderId ?? "";
    this.capacityTokens = opts?.capacityTokens ?? 100_000;
    this.durationSeconds = opts?.durationSeconds ?? 3600;
    this.priceUsd = opts?.priceUsd ?? 0.0;
    this.qosTier = opts?.qosTier ?? QoSTier.RESERVED;
    this.autoRenew = opts?.autoRenew ?? false;
    this.timestamp = opts?.timestamp ?? new Date().toISOString();
  }

  toDict(): ContextReservationData {
    return {
      reservation_id: this.reservationId,
      requestor_id: this.requestorId,
      responder_id: this.responderId,
      capacity_tokens: this.capacityTokens,
      duration_seconds: this.durationSeconds,
      price_usd: this.priceUsd,
      qos_tier: this.qosTier,
      auto_renew: this.autoRenew,
      timestamp: this.timestamp,
    };
  }

  static fromDict(d: Partial<ContextReservationData>): ContextReservation {
    return new ContextReservation({
      reservationId: d.reservation_id,
      requestorId: d.requestor_id,
      responderId: d.responder_id,
      capacityTokens: d.capacity_tokens,
      durationSeconds: d.duration_seconds,
      priceUsd: d.price_usd,
      qosTier: d.qos_tier,
      autoRenew: d.auto_renew,
      timestamp: d.timestamp,
    });
  }
}
