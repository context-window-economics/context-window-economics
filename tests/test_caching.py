"""Tests for caching.py — cache economics, compression ROI, memory analysis."""
from context_window_economics.caching import (
    CacheTracker,
    cache_amortized_cost,
    compression_roi,
    memory_vs_context_crossover,
)


def test_cache_amortized_cost_whitepaper():
    """Test against whitepaper Section 12.2 example."""
    result = cache_amortized_cost(
        context_tokens=100000,
        input_rate_per_mtok=3.0,  # Sonnet 4.6
        cache_write_multiplier=1.25,
        cache_hit_rate=0.10,
        num_interactions=10,
    )
    # First: 100K * 3.0/1M * 1.25 = $0.375
    assert abs(result["first_cost"] - 0.375) < 1e-6
    # Subsequent: 100K * 3.0/1M * 0.10 = $0.030
    assert abs(result["subsequent_cost"] - 0.030) < 1e-6
    # Amortized: (0.375 + 9 * 0.030) / 10 = 0.0645
    assert abs(result["amortized_cost"] - 0.0645) < 1e-6
    # Savings: ~78%
    assert result["savings_pct"] > 75.0


def test_cache_amortized_single():
    result = cache_amortized_cost(
        context_tokens=100000,
        input_rate_per_mtok=3.0,
        num_interactions=1,
    )
    # Only first interaction — amortized = first_cost
    assert abs(result["amortized_cost"] - result["first_cost"]) < 1e-6


def test_compression_roi():
    result = compression_roi(
        uncompressed_tokens=50000,
        compressed_tokens=5000,
        input_rate_per_mtok=3.0,
        compressor_output_rate_per_mtok=15.0,
        compressor_tokens=1000,
    )
    # Savings: (50000 - 5000) * 3.0/1M = 45000 * 0.000003 = $0.135
    assert abs(result["savings"] - 0.135) < 1e-6
    # Cost: 1000 * 15.0/1M = $0.015
    assert abs(result["cost"] - 0.015) < 1e-6
    # Net: 0.135 - 0.015 = 0.12
    assert abs(result["net_savings"] - 0.12) < 1e-6
    # ROI: 0.12 / 0.015 = 8.0
    assert abs(result["roi"] - 8.0) < 1e-6
    # Compression ratio: 50000 / 5000 = 10.0
    assert abs(result["compression_ratio"] - 10.0) < 1e-6


def test_compression_roi_no_compressor():
    """When compression is free (e.g., simple truncation)."""
    result = compression_roi(
        uncompressed_tokens=10000,
        compressed_tokens=5000,
        input_rate_per_mtok=3.0,
    )
    assert result["cost"] == 0.0
    assert result["net_savings"] == result["savings"]


def test_memory_vs_context_crossover():
    result = memory_vs_context_crossover(
        context_tokens=100000,
        input_rate_per_mtok=3.0,
        memory_write_cost=0.01,
        memory_read_cost_per_interaction=0.005,
    )
    # Context cost per interaction: 100K * 3.0/1M = $0.30
    # Memory: 0.01 + n * 0.005
    # Crossover: 0.01 + n * 0.005 <= n * 0.30 → n >= 0.01/0.295 ≈ 1
    assert result["crossover_point"] == 1  # Memory is cheaper almost immediately with these params
    assert result["recommendation"] == "memory"
    assert len(result["memory_costs"]) == 50
    assert len(result["context_costs"]) == 50


def test_memory_vs_context_expensive_memory():
    result = memory_vs_context_crossover(
        context_tokens=1000,
        input_rate_per_mtok=0.25,  # Haiku — very cheap
        memory_write_cost=0.10,
        memory_read_cost_per_interaction=0.05,
    )
    # Context: 1000 * 0.25/1M = $0.00025 per interaction
    # Memory: 0.10 + n * 0.05
    # Memory never cheaper if 0.05 > 0.00025
    assert result["crossover_point"] == -1
    assert result["recommendation"] == "long_context"


def test_cache_tracker():
    tracker = CacheTracker()
    tracker.record_hit(5000, rate_per_mtok=3.0)
    tracker.record_hit(3000, rate_per_mtok=3.0)
    tracker.record_miss(10000)

    assert tracker.hits == 2
    assert tracker.misses == 1
    assert tracker.total_cached_tokens == 8000
    assert tracker.total_uncached_tokens == 10000
    assert abs(tracker.hit_rate - 2.0 / 3.0) < 1e-6
    assert tracker.estimated_savings_usd > 0

    summary = tracker.summary()
    assert summary["hits"] == 2
    assert summary["hit_rate"] == tracker.hit_rate
