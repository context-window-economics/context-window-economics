import {
  DEFAULT_DEPOSIT_MULTIPLIER,
  DepositRecord,
  DepositStatus,
  PROGRESSIVE_REQUEST_LIMITS,
  REPUTATION_DEPOSIT_MULTIPLIERS,
  REPUTATION_THRESHOLDS,
  ReputationTier,
} from "./types";

export function classifyReputation(score: number): string {
  if (score > REPUTATION_THRESHOLDS[ReputationTier.HIGH]) {
    return ReputationTier.HIGH;
  } else if (score > REPUTATION_THRESHOLDS[ReputationTier.MEDIUM]) {
    return ReputationTier.MEDIUM;
  } else if (score >= 0) {
    return ReputationTier.LOW;
  }
  return ReputationTier.UNKNOWN;
}

export function depositMultiplierForTier(tier: string): number {
  return REPUTATION_DEPOSIT_MULTIPLIERS[tier] ?? DEFAULT_DEPOSIT_MULTIPLIER;
}

export function calculateDeposit(
  estimatedRequestTokens: number,
  responderInputRatePerMtok: number,
  reputationScore: number = -1.0,
  baseMultiplier: number = DEFAULT_DEPOSIT_MULTIPLIER
): [number, string] {
  let tier: string;
  if (reputationScore < 0) {
    tier = ReputationTier.UNKNOWN;
  } else {
    tier = classifyReputation(reputationScore);
  }

  const repMultiplier = depositMultiplierForTier(tier);
  if (repMultiplier === 0.0) {
    return [0.0, tier];
  }

  const processingCost =
    (estimatedRequestTokens * responderInputRatePerMtok) / 1_000_000;
  const deposit = processingCost * baseMultiplier * repMultiplier;

  return [deposit, tier];
}

export function maxRequestTokens(
  reputationScore: number,
  interactionCount: number
): number {
  for (const level of PROGRESSIVE_REQUEST_LIMITS) {
    if (
      reputationScore < level.max_reputation &&
      interactionCount < level.max_interactions
    ) {
      return level.max_tokens;
    }
  }
  return -1;
}

export function checkAccess(
  reputationScore: number,
  interactionCount: number,
  requestTokens: number
): [boolean, string] {
  const limit = maxRequestTokens(reputationScore, interactionCount);
  if (limit === -1) {
    return [true, "unlimited"];
  }
  if (requestTokens > limit) {
    return [
      false,
      `Request size ${requestTokens} exceeds progressive limit ` +
        `${limit} for reputation=${reputationScore.toFixed(0)}, ` +
        `interactions=${interactionCount}`,
    ];
  }
  return [true, "within_limits"];
}

export function createDeposit(opts: {
  requestorId: string;
  responderId: string;
  estimatedRequestTokens: number;
  responderInputRatePerMtok: number;
  reputationScore?: number;
  baseMultiplier?: number;
  interactionId?: string;
}): DepositRecord {
  const [amount, tier] = calculateDeposit(
    opts.estimatedRequestTokens,
    opts.responderInputRatePerMtok,
    opts.reputationScore ?? -1.0,
    opts.baseMultiplier ?? DEFAULT_DEPOSIT_MULTIPLIER
  );
  return new DepositRecord({
    requestorId: opts.requestorId,
    responderId: opts.responderId,
    amountUsd: amount,
    status: DepositStatus.COMMITTED,
    interactionId: opts.interactionId ?? null,
    multiplier: opts.baseMultiplier ?? DEFAULT_DEPOSIT_MULTIPLIER,
    reputationTier: tier,
  });
}

export function resolveDeposit(
  deposit: DepositRecord,
  isSpam: boolean
): DepositRecord {
  if (isSpam) {
    deposit.status = DepositStatus.FORFEITED;
  } else {
    deposit.status = DepositStatus.REFUNDED;
  }
  return deposit;
}
