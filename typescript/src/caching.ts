export interface CacheAmortizedCostResult {
  first_cost: number;
  subsequent_cost: number;
  amortized_cost: number;
  uncached_cost: number;
  total_cached: number;
  total_uncached: number;
  savings_pct: number;
}

export interface CompressionRoiResult {
  savings: number;
  cost: number;
  net_savings: number;
  roi: number;
  compression_ratio: number;
}

export interface CacheTrackerSummary {
  hits: number;
  misses: number;
  hit_rate: number;
  total_cached_tokens: number;
  total_uncached_tokens: number;
  estimated_savings_usd: number;
}

export interface MemoryVsContextCrossoverResult {
  crossover_point: number;
  memory_costs: number[];
  context_costs: number[];
  recommendation: string;
}

// ---------------------------------------------------------------------------
// Cache economics (Section 12.2)
// ---------------------------------------------------------------------------

export function cacheAmortizedCost(opts: {
  contextTokens: number;
  inputRatePerMtok: number;
  cacheWriteMultiplier?: number;
  cacheHitRate?: number;
  numInteractions?: number;
}): CacheAmortizedCostResult {
  const cacheWriteMultiplier = opts.cacheWriteMultiplier ?? 1.25;
  const cacheHitRate = opts.cacheHitRate ?? 0.1;
  const n = Math.max(1, opts.numInteractions ?? 10);

  const baseCost =
    (opts.contextTokens * opts.inputRatePerMtok) / 1_000_000;

  const firstCost = baseCost * cacheWriteMultiplier;
  const subsequentCost = baseCost * cacheHitRate;

  const totalCached = firstCost + (n - 1) * subsequentCost;
  const totalUncached = baseCost * n;
  const amortized = totalCached / n;

  let savingsPct = 0.0;
  if (totalUncached > 0) {
    savingsPct = (1.0 - totalCached / totalUncached) * 100.0;
  }

  return {
    first_cost: firstCost,
    subsequent_cost: subsequentCost,
    amortized_cost: amortized,
    uncached_cost: baseCost,
    total_cached: totalCached,
    total_uncached: totalUncached,
    savings_pct: savingsPct,
  };
}

// ---------------------------------------------------------------------------
// Compression ROI (Section 12.1)
// ---------------------------------------------------------------------------

export function compressionRoi(opts: {
  uncompressedTokens: number;
  compressedTokens: number;
  inputRatePerMtok: number;
  compressorOutputRatePerMtok?: number;
  compressorTokens?: number;
}): CompressionRoiResult {
  const compressorOutputRate = opts.compressorOutputRatePerMtok ?? 0.0;
  const compressorTokens = opts.compressorTokens ?? 0;

  const savings =
    ((opts.uncompressedTokens - opts.compressedTokens) *
      opts.inputRatePerMtok) /
    1_000_000;
  const cost = (compressorTokens * compressorOutputRate) / 1_000_000;
  const netSavings = savings - cost;

  let roi = 0.0;
  if (cost > 0) {
    roi = netSavings / cost;
  }

  let compressionRatio = 0.0;
  if (opts.compressedTokens > 0) {
    compressionRatio = opts.uncompressedTokens / opts.compressedTokens;
  }

  return {
    savings,
    cost,
    net_savings: netSavings,
    roi,
    compression_ratio: compressionRatio,
  };
}

// ---------------------------------------------------------------------------
// Memory vs. long-context analysis (Section 12.3)
// ---------------------------------------------------------------------------

export function memoryVsContextCrossover(opts: {
  contextTokens: number;
  inputRatePerMtok: number;
  memoryWriteCost?: number;
  memoryReadCostPerInteraction?: number;
  maxInteractions?: number;
}): MemoryVsContextCrossoverResult {
  const memoryWriteCost = opts.memoryWriteCost ?? 0.01;
  const memoryReadCostPerInteraction =
    opts.memoryReadCostPerInteraction ?? 0.005;
  const maxInteractions = opts.maxInteractions ?? 50;

  const contextCostPerInteraction =
    (opts.contextTokens * opts.inputRatePerMtok) / 1_000_000;

  let crossover = -1;
  const memoryCosts: number[] = [];
  const contextCosts: number[] = [];

  for (let n = 1; n <= maxInteractions; n++) {
    const memTotal = memoryWriteCost + n * memoryReadCostPerInteraction;
    const ctxTotal = n * contextCostPerInteraction;
    memoryCosts.push(memTotal);
    contextCosts.push(ctxTotal);

    if (crossover === -1 && memTotal <= ctxTotal) {
      crossover = n;
    }
  }

  let recommendation: string;
  if (crossover === -1) {
    recommendation = "long_context";
  } else if (crossover <= 5) {
    recommendation = "memory";
  } else {
    recommendation = "memory_after_" + crossover;
  }

  return {
    crossover_point: crossover,
    memory_costs: memoryCosts,
    context_costs: contextCosts,
    recommendation,
  };
}

// ---------------------------------------------------------------------------
// Cache hit/miss tracker
// ---------------------------------------------------------------------------

export class CacheTracker {
  hits: number = 0;
  misses: number = 0;
  totalCachedTokens: number = 0;
  totalUncachedTokens: number = 0;
  estimatedSavingsUsd: number = 0.0;

  recordHit(cachedTokens: number, ratePerMtok: number): void {
    this.hits += 1;
    this.totalCachedTokens += cachedTokens;
    this.estimatedSavingsUsd +=
      (cachedTokens * ratePerMtok * 0.9) / 1_000_000;
  }

  recordMiss(tokens: number): void {
    this.misses += 1;
    this.totalUncachedTokens += tokens;
  }

  get hitRate(): number {
    const total = this.hits + this.misses;
    return total > 0 ? this.hits / total : 0.0;
  }

  get totalInteractions(): number {
    return this.hits + this.misses;
  }

  summary(): CacheTrackerSummary {
    return {
      hits: this.hits,
      misses: this.misses,
      hit_rate: this.hitRate,
      total_cached_tokens: this.totalCachedTokens,
      total_uncached_tokens: this.totalUncachedTokens,
      estimated_savings_usd: this.estimatedSavingsUsd,
    };
  }
}
