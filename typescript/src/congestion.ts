import {
  BackPressureSignal,
  BackPressureStatus,
  CongestionLevel,
  PROTOCOL_OVERHEAD_TOKENS,
  QoSConfig,
  QoSTier,
  QOS_RATE_MULTIPLIERS,
} from "./types";

export interface EffectiveTokenPriceResult {
  btc: number;
  cp: number;
  po: number;
  total: number;
  congestion_multiplier: number;
  qos_multiplier: number;
}

export interface QosCheckResult {
  size_ok: boolean;
  utilization_ok: boolean;
  allowed: boolean;
}

// ---------------------------------------------------------------------------
// Congestion multiplier (Section 9.1)
// ---------------------------------------------------------------------------

export function congestionMultiplier(utilization: number): number {
  const u = Math.max(0.0, Math.min(1.0, utilization));
  if (u < 0.5) return 1.0;
  if (u < 0.8) return 1.0 + 0.5 * u;
  if (u < 0.95) return 1.0 + 2.0 * u;
  return 1.0 + 5.0 * u;
}

export function congestionLevel(utilization: number): string {
  const u = Math.max(0.0, Math.min(1.0, utilization));
  if (u < 0.5) return CongestionLevel.ABUNDANT;
  if (u < 0.8) return CongestionLevel.MODERATE;
  if (u < 0.95) return CongestionLevel.HEAVY;
  return CongestionLevel.CRITICAL;
}

// ---------------------------------------------------------------------------
// Three-component pricing (Section 9.1)
// ---------------------------------------------------------------------------

export function effectiveTokenPrice(opts: {
  baseRatePerMtok: number;
  tokens: number;
  utilization?: number;
  overheadTokens?: number;
  qosTier?: string;
}): EffectiveTokenPriceResult {
  const utilization = opts.utilization ?? 0.0;
  const overheadTokens = opts.overheadTokens ?? PROTOCOL_OVERHEAD_TOKENS;
  const qosTier = opts.qosTier ?? QoSTier.STANDARD;

  const qosMult = QOS_RATE_MULTIPLIERS[qosTier] ?? 1.0;
  const congMult = congestionMultiplier(utilization);

  const btc = (opts.tokens * opts.baseRatePerMtok) / 1_000_000 * qosMult;
  const cp = btc * (congMult - 1.0);
  const po = (overheadTokens * opts.baseRatePerMtok) / 1_000_000;

  return {
    btc,
    cp,
    po,
    total: btc + cp + po,
    congestion_multiplier: congMult,
    qos_multiplier: qosMult,
  };
}

// ---------------------------------------------------------------------------
// Position-dependent pricing (Section 9.2)
// ---------------------------------------------------------------------------

export function positionMultiplier(
  position: number,
  windowSize: number,
  beta: number = 0.3
): number {
  if (windowSize <= 0 || position <= 0) return 0.0;
  const ratio = Math.min(position / windowSize, 1.0);
  return ratio ** beta;
}

// ---------------------------------------------------------------------------
// QoS tier management
// ---------------------------------------------------------------------------

export function qosConfigForTier(tier: string): QoSConfig {
  const configs: Record<string, QoSConfig> = {
    [QoSTier.ECONOMY]: new QoSConfig({
      tier: QoSTier.ECONOMY,
      inputTokensPerMinute: 500_000,
      outputTokensPerMinute: 100_000,
      concurrentInteractions: 5,
      maxRequestSizeTokens: 200_000,
      maxContextUtilization: 0.6,
    }),
    [QoSTier.STANDARD]: new QoSConfig({
      tier: QoSTier.STANDARD,
      inputTokensPerMinute: 1_000_000,
      outputTokensPerMinute: 200_000,
      concurrentInteractions: 10,
      maxRequestSizeTokens: 500_000,
      maxContextUtilization: 0.8,
    }),
    [QoSTier.PRIORITY]: new QoSConfig({
      tier: QoSTier.PRIORITY,
      inputTokensPerMinute: 2_000_000,
      outputTokensPerMinute: 500_000,
      concurrentInteractions: 20,
      maxRequestSizeTokens: 800_000,
      maxContextUtilization: 0.9,
    }),
    [QoSTier.RESERVED]: new QoSConfig({
      tier: QoSTier.RESERVED,
      inputTokensPerMinute: 5_000_000,
      outputTokensPerMinute: 1_000_000,
      concurrentInteractions: 50,
      maxRequestSizeTokens: 1_000_000,
      maxContextUtilization: 0.95,
    }),
  };
  return configs[tier] ?? configs[QoSTier.STANDARD];
}

export function checkQosLimits(
  config: QoSConfig,
  requestTokens: number,
  currentUtilization: number
): QosCheckResult {
  const sizeOk = requestTokens <= config.maxRequestSizeTokens;
  const utilOk = currentUtilization <= config.maxContextUtilization;
  return {
    size_ok: sizeOk,
    utilization_ok: utilOk,
    allowed: sizeOk && utilOk,
  };
}

// ---------------------------------------------------------------------------
// Back-pressure signaling (Section 10.4)
// ---------------------------------------------------------------------------

export function generateBackPressure(
  utilization: number,
  queueDepth: number = 0,
  estimatedQueueMs: number = 0
): BackPressureSignal {
  const level = congestionLevel(utilization);

  let status: string;
  let available: string[];

  if (level === CongestionLevel.ABUNDANT) {
    status = BackPressureStatus.OK;
    available = [QoSTier.ECONOMY, QoSTier.STANDARD, QoSTier.PRIORITY, QoSTier.RESERVED];
  } else if (
    level === CongestionLevel.MODERATE ||
    level === CongestionLevel.HEAVY
  ) {
    status = BackPressureStatus.CONGESTED;
    available = [QoSTier.STANDARD, QoSTier.PRIORITY, QoSTier.RESERVED];
  } else {
    status = BackPressureStatus.OVERLOADED;
    available = [QoSTier.PRIORITY, QoSTier.RESERVED];
  }

  return new BackPressureSignal({
    cwepStatus: status,
    currentUtilization: utilization,
    estimatedQueueTimeMs: estimatedQueueMs,
    availableTiers: available,
    economyQueueDepth: queueDepth,
  });
}
