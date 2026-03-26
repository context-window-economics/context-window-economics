"""Tests for congestion.py — pricing, QoS, back-pressure."""
from context_window_economics.congestion import (
    check_qos_limits,
    congestion_level,
    congestion_multiplier,
    effective_token_price,
    generate_back_pressure,
    position_multiplier,
    qos_config_for_tier,
)
from context_window_economics.schema import (
    BackPressureStatus,
    CongestionLevel,
    QoSTier,
)


def test_congestion_multiplier_abundant():
    assert congestion_multiplier(0.0) == 1.0
    assert congestion_multiplier(0.30) == 1.0
    assert congestion_multiplier(0.49) == 1.0


def test_congestion_multiplier_moderate():
    # At 0.60: 1.0 + 0.5 * 0.60 = 1.30
    assert abs(congestion_multiplier(0.60) - 1.30) < 1e-6


def test_congestion_multiplier_heavy():
    # At 0.90: 1.0 + 2.0 * 0.90 = 2.80
    assert abs(congestion_multiplier(0.90) - 2.80) < 1e-6


def test_congestion_multiplier_critical():
    # At 0.95: 1.0 + 5.0 * 0.95 = 5.75
    assert abs(congestion_multiplier(0.95) - 5.75) < 1e-6


def test_congestion_level_classification():
    assert congestion_level(0.30) == CongestionLevel.ABUNDANT.value
    assert congestion_level(0.60) == CongestionLevel.MODERATE.value
    assert congestion_level(0.85) == CongestionLevel.HEAVY.value
    assert congestion_level(0.96) == CongestionLevel.CRITICAL.value


def test_effective_token_price_no_congestion():
    result = effective_token_price(
        base_rate_per_mtok=3.0,
        tokens=100000,
        utilization=0.30,
    )
    # BTC = 100000 * 3.0/1M = 0.30 (no congestion premium at < 50%)
    assert abs(result["btc"] - 0.30) < 1e-6
    assert abs(result["cp"]) < 1e-6  # No congestion
    assert result["po"] > 0  # Protocol overhead


def test_effective_token_price_with_congestion():
    result = effective_token_price(
        base_rate_per_mtok=3.0,
        tokens=100000,
        utilization=0.90,
    )
    # BTC = 0.30
    # CP = 0.30 * (2.80 - 1.0) = 0.30 * 1.80 = 0.54
    assert abs(result["btc"] - 0.30) < 1e-6
    assert abs(result["cp"] - 0.54) < 1e-6


def test_effective_token_price_priority_tier():
    result = effective_token_price(
        base_rate_per_mtok=3.0,
        tokens=100000,
        utilization=0.30,
        qos_tier=QoSTier.PRIORITY.value,
    )
    # BTC = 100000 * 3.0/1M * 2.0 = 0.60 (2x for priority)
    assert abs(result["btc"] - 0.60) < 1e-6
    assert result["qos_multiplier"] == 2.0


def test_position_multiplier():
    # At position 10K in 1M window, beta=0.3
    m = position_multiplier(10000, 1000000, beta=0.3)
    # (10000/1000000)^0.3 = 0.01^0.3 ≈ 0.251
    assert abs(m - 0.251) < 0.01

    # At position 500K
    m2 = position_multiplier(500000, 1000000, beta=0.3)
    # 0.5^0.3 ≈ 0.812
    assert abs(m2 - 0.812) < 0.01

    # Edge: position 0
    assert position_multiplier(0, 1000000) == 0.0


def test_qos_config_for_tier():
    economy = qos_config_for_tier(QoSTier.ECONOMY.value)
    assert economy.max_context_utilization == 0.60

    reserved = qos_config_for_tier(QoSTier.RESERVED.value)
    assert reserved.max_context_utilization == 0.95
    assert reserved.concurrent_interactions == 50


def test_check_qos_limits_ok():
    config = qos_config_for_tier(QoSTier.STANDARD.value)
    result = check_qos_limits(config, request_tokens=100000, current_utilization=0.50)
    assert result["allowed"] is True


def test_check_qos_limits_too_large():
    config = qos_config_for_tier(QoSTier.ECONOMY.value)
    result = check_qos_limits(config, request_tokens=300000, current_utilization=0.30)
    assert result["size_ok"] is False
    assert result["allowed"] is False


def test_check_qos_limits_utilization_exceeded():
    config = qos_config_for_tier(QoSTier.ECONOMY.value)
    result = check_qos_limits(config, request_tokens=100000, current_utilization=0.70)
    assert result["utilization_ok"] is False


def test_back_pressure_ok():
    bp = generate_back_pressure(utilization=0.30)
    assert bp.cwep_status == BackPressureStatus.OK.value
    assert len(bp.available_tiers) == 4


def test_back_pressure_congested():
    bp = generate_back_pressure(utilization=0.70, queue_depth=5, estimated_queue_ms=2000)
    assert bp.cwep_status == BackPressureStatus.CONGESTED.value
    assert QoSTier.ECONOMY.value not in bp.available_tiers


def test_back_pressure_overloaded():
    bp = generate_back_pressure(utilization=0.96, queue_depth=20, estimated_queue_ms=10000)
    assert bp.cwep_status == BackPressureStatus.OVERLOADED.value
    assert len(bp.available_tiers) == 2
