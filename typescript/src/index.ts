// Types, constants, enums
export {
  PROTOCOL_VERSION,
  SCHEMA_VERSION,
  DEFAULT_PROVIDER_PRICING,
  DEFAULT_SETTLEMENT_THRESHOLD,
  DEFAULT_DEPOSIT_MULTIPLIER,
  DEFAULT_BATCH_WINDOW_SECONDS,
  DEFAULT_BATCH_THRESHOLD_USD,
  MAX_CMR_SIZE_BYTES,
  PROTOCOL_OVERHEAD_TOKENS,
  QOS_RATE_MULTIPLIERS,
  REPUTATION_DEPOSIT_MULTIPLIERS,
  REPUTATION_THRESHOLDS,
  PROGRESSIVE_REQUEST_LIMITS,
  CostFlow,
  AllocationMethod,
  SettlementTier,
  QoSTier,
  CongestionLevel,
  ReputationTier,
  DepositStatus,
  BackPressureStatus,
  AgentPricing,
  AgentInfo,
  TokenFlow,
  InteractionTotals,
  ContextState,
  SettlementProposal,
  CostMeteringRecord,
  DepositRecord,
  QoSConfig,
  BackPressureSignal,
  ContextReservation,
} from "./types";
export type {
  AgentPricingData,
  AgentInfoData,
  TokenFlowData,
  InteractionTotalsData,
  ContextStateData,
  SettlementProposalData,
  CostMeteringRecordData,
  DepositRecordData,
  QoSConfigData,
  BackPressureSignalData,
  ContextReservationData,
} from "./types";

// Metering
export { Meter, computeFlowCost, estimateInteractionCost } from "./metering";
export type { InteractionCostEstimate } from "./metering";

// Allocation
export {
  allocate,
  allocateRequestorPays,
  allocateResponderPays,
  allocateEqualSplit,
  allocateProportional,
  allocateShapley,
  allocateNash,
} from "./allocation";

// Settlement
export {
  PaymentRail,
  SettlementReceipt,
  SettlementEngine,
  SettlementBatch,
  cmrHash,
  verifyCmrPair,
} from "./settlement";
export type { SettlementReceiptData } from "./settlement";

// Spam prevention
export {
  classifyReputation,
  depositMultiplierForTier,
  calculateDeposit,
  maxRequestTokens,
  checkAccess,
  createDeposit,
  resolveDeposit,
} from "./spam";

// Congestion pricing
export {
  congestionMultiplier,
  congestionLevel,
  effectiveTokenPrice,
  positionMultiplier,
  qosConfigForTier,
  checkQosLimits,
  generateBackPressure,
} from "./congestion";
export type { EffectiveTokenPriceResult, QosCheckResult } from "./congestion";

// Caching economics
export {
  cacheAmortizedCost,
  compressionRoi,
  memoryVsContextCrossover,
  CacheTracker,
} from "./caching";
export type {
  CacheAmortizedCostResult,
  CompressionRoiResult,
  MemoryVsContextCrossoverResult,
  CacheTrackerSummary,
} from "./caching";

// Store
export { CWEPStore } from "./store";
