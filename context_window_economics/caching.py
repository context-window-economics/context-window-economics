"""Prompt caching economics, compression ROI, and memory vs. long-context analysis.

Implements Section 12 of the CWEP whitepaper:
  - Cache cost amortization across repeated interactions
  - Cache hit/miss tracking
  - Compression ROI calculation
  - Memory vs. long-context crossover analysis
"""
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Cache economics (Section 12.2)
# ---------------------------------------------------------------------------

def cache_amortized_cost(
    context_tokens: int,
    input_rate_per_mtok: float,
    cache_write_multiplier: float = 1.25,
    cache_hit_rate: float = 0.10,
    num_interactions: int = 10,
) -> Dict[str, float]:
    """Compute amortized per-interaction cost with prompt caching.

    From the whitepaper (Section 12.2):
        first_cost = tokens * rate * cache_write_multiplier
        subsequent_cost = tokens * rate * cache_hit_rate
        amortized = (first + (n-1) * subsequent) / n

    Args:
        context_tokens: Tokens in the cached context.
        input_rate_per_mtok: Input rate per MTok.
        cache_write_multiplier: Multiplier for initial cache write (e.g., 1.25).
        cache_hit_rate: Fraction of base cost for cache hits (e.g., 0.10).
        num_interactions: Number of interactions to amortize over.

    Returns:
        Dict with first_cost, subsequent_cost, amortized_cost, uncached_cost,
        total_cached, total_uncached, savings_pct.
    """
    base_cost = context_tokens * input_rate_per_mtok / 1_000_000

    first_cost = base_cost * cache_write_multiplier
    subsequent_cost = base_cost * cache_hit_rate

    n = max(1, num_interactions)
    total_cached = first_cost + (n - 1) * subsequent_cost
    total_uncached = base_cost * n
    amortized = total_cached / n

    savings_pct = 0.0
    if total_uncached > 0:
        savings_pct = (1.0 - total_cached / total_uncached) * 100.0

    return {
        "first_cost": first_cost,
        "subsequent_cost": subsequent_cost,
        "amortized_cost": amortized,
        "uncached_cost": base_cost,
        "total_cached": total_cached,
        "total_uncached": total_uncached,
        "savings_pct": savings_pct,
    }


# ---------------------------------------------------------------------------
# Compression ROI (Section 12.1)
# ---------------------------------------------------------------------------

def compression_roi(
    uncompressed_tokens: int,
    compressed_tokens: int,
    input_rate_per_mtok: float,
    compressor_output_rate_per_mtok: float = 0.0,
    compressor_tokens: int = 0,
) -> Dict[str, float]:
    """Compute ROI for prompt compression.

    From the whitepaper (Section 12.1):
        compression_savings = (uncompressed - compressed) * input_rate
        compression_cost = compressor_tokens * compressor_output_rate
        net_savings = savings - cost
        roi = net_savings / cost  (if cost > 0)

    Args:
        uncompressed_tokens: Original token count.
        compressed_tokens: Token count after compression.
        input_rate_per_mtok: Input rate for the tokens being compressed.
        compressor_output_rate_per_mtok: Output rate for the compression model.
        compressor_tokens: Tokens consumed by the compression process.

    Returns:
        Dict with savings, cost, net_savings, roi, compression_ratio.
    """
    savings = (uncompressed_tokens - compressed_tokens) * input_rate_per_mtok / 1_000_000
    cost = compressor_tokens * compressor_output_rate_per_mtok / 1_000_000
    net_savings = savings - cost

    roi = 0.0
    if cost > 0:
        roi = net_savings / cost

    compression_ratio = 0.0
    if compressed_tokens > 0:
        compression_ratio = uncompressed_tokens / compressed_tokens

    return {
        "savings": savings,
        "cost": cost,
        "net_savings": net_savings,
        "roi": roi,
        "compression_ratio": compression_ratio,
    }


# ---------------------------------------------------------------------------
# Memory vs. long-context analysis (Section 12.3)
# ---------------------------------------------------------------------------

def memory_vs_context_crossover(
    context_tokens: int,
    input_rate_per_mtok: float,
    memory_write_cost: float = 0.01,
    memory_read_cost_per_interaction: float = 0.005,
    max_interactions: int = 50,
) -> Dict[str, object]:
    """Determine the crossover point where memory becomes cheaper than long-context.

    From the whitepaper (Section 12.3):
        At < ~10 interactions, long-context is cheaper (lower setup cost).
        At > ~10 interactions, memory becomes cheaper (lower marginal cost).

    Args:
        context_tokens: Tokens that would be held in context.
        input_rate_per_mtok: Per-MTok input rate.
        memory_write_cost: One-time cost to write to memory system.
        memory_read_cost_per_interaction: Per-interaction cost to read from memory.
        max_interactions: Range of interactions to analyze.

    Returns:
        Dict with crossover_point, memory_costs, context_costs, recommendation.
    """
    context_cost_per_interaction = context_tokens * input_rate_per_mtok / 1_000_000

    crossover = -1
    memory_costs = []
    context_costs = []

    for n in range(1, max_interactions + 1):
        mem_total = memory_write_cost + n * memory_read_cost_per_interaction
        ctx_total = n * context_cost_per_interaction
        memory_costs.append(mem_total)
        context_costs.append(ctx_total)

        if crossover == -1 and mem_total <= ctx_total:
            crossover = n

    if crossover == -1:
        recommendation = "long_context"
    elif crossover <= 5:
        recommendation = "memory"
    else:
        recommendation = "memory_after_" + str(crossover)

    return {
        "crossover_point": crossover,
        "memory_costs": memory_costs,
        "context_costs": context_costs,
        "recommendation": recommendation,
    }


# ---------------------------------------------------------------------------
# Cache hit/miss tracker
# ---------------------------------------------------------------------------

@dataclass
class CacheTracker:
    """Tracks cache hit/miss statistics for an agent's interactions."""
    hits: int = 0
    misses: int = 0
    total_cached_tokens: int = 0
    total_uncached_tokens: int = 0
    estimated_savings_usd: float = 0.0

    def record_hit(self, cached_tokens: int, rate_per_mtok: float) -> None:
        """Record a cache hit."""
        self.hits += 1
        self.total_cached_tokens += cached_tokens
        # Savings = (full_rate - cache_rate) * tokens; assume cache is 10% of full
        self.estimated_savings_usd += cached_tokens * rate_per_mtok * 0.90 / 1_000_000

    def record_miss(self, tokens: int) -> None:
        """Record a cache miss."""
        self.misses += 1
        self.total_uncached_tokens += tokens

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_interactions(self) -> int:
        return self.hits + self.misses

    def summary(self) -> Dict[str, object]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "total_cached_tokens": self.total_cached_tokens,
            "total_uncached_tokens": self.total_uncached_tokens,
            "estimated_savings_usd": self.estimated_savings_usd,
        }
