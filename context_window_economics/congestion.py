"""Congestion pricing, QoS tiers, and back-pressure signaling.

Implements Sections 9 and 10 of the CWEP whitepaper:
  - Three-component pricing model (base + congestion + overhead)
  - Utilization-based congestion multipliers
  - QoS tiers (economy, standard, priority, reserved)
  - Back-pressure signals
  - Position-dependent pricing (experimental extension)
"""
from typing import Dict, List, Optional

from .schema import (
    BackPressureSignal,
    BackPressureStatus,
    CongestionLevel,
    PROTOCOL_OVERHEAD_TOKENS,
    QoSConfig,
    QoSTier,
    QOS_RATE_MULTIPLIERS,
)


# ---------------------------------------------------------------------------
# Congestion multiplier (Section 9.1)
# ---------------------------------------------------------------------------

def congestion_multiplier(utilization: float) -> float:
    """Compute the congestion multiplier for a given context utilization.

    From the whitepaper (Section 9.1):
        1.0            if u < 0.50     (abundant)
        1.0 + 0.5*u    if 0.50 <= u < 0.80  (moderate)
        1.0 + 2.0*u    if 0.80 <= u < 0.95  (heavy)
        1.0 + 5.0*u    if u >= 0.95    (critical)

    Args:
        utilization: Context window utilization as fraction (0.0 to 1.0).

    Returns:
        Congestion multiplier (>= 1.0).
    """
    u = max(0.0, min(1.0, utilization))
    if u < 0.50:
        return 1.0
    elif u < 0.80:
        return 1.0 + 0.5 * u
    elif u < 0.95:
        return 1.0 + 2.0 * u
    else:
        return 1.0 + 5.0 * u


def congestion_level(utilization: float) -> str:
    """Classify utilization into a congestion level.

    Args:
        utilization: Context window utilization as fraction.

    Returns:
        CongestionLevel value string.
    """
    u = max(0.0, min(1.0, utilization))
    if u < 0.50:
        return CongestionLevel.ABUNDANT.value
    elif u < 0.80:
        return CongestionLevel.MODERATE.value
    elif u < 0.95:
        return CongestionLevel.HEAVY.value
    return CongestionLevel.CRITICAL.value


# ---------------------------------------------------------------------------
# Three-component pricing (Section 9.1)
# ---------------------------------------------------------------------------

def effective_token_price(
    base_rate_per_mtok: float,
    tokens: int,
    utilization: float = 0.0,
    overhead_tokens: int = PROTOCOL_OVERHEAD_TOKENS,
    qos_tier: str = QoSTier.STANDARD.value,
) -> Dict[str, float]:
    """Compute the three-component effective token price.

    From the whitepaper:
        effective_price = BTC + CP + PO

    Where:
        BTC = base_rate * tokens
        CP  = BTC * congestion_multiplier(utilization) - BTC  [the premium portion]
        PO  = overhead_tokens * base_rate (input)

    Args:
        base_rate_per_mtok: Provider's per-MTok rate.
        tokens: Number of tokens being priced.
        utilization: Responder's current context utilization.
        overhead_tokens: Protocol overhead tokens.
        qos_tier: Quality-of-service tier.

    Returns:
        Dict with btc, cp, po, total, congestion_multiplier, qos_multiplier.
    """
    qos_mult = QOS_RATE_MULTIPLIERS.get(qos_tier, 1.0)
    cong_mult = congestion_multiplier(utilization)

    btc = tokens * base_rate_per_mtok / 1_000_000 * qos_mult
    cp = btc * (cong_mult - 1.0)
    po = overhead_tokens * base_rate_per_mtok / 1_000_000

    return {
        "btc": btc,
        "cp": cp,
        "po": po,
        "total": btc + cp + po,
        "congestion_multiplier": cong_mult,
        "qos_multiplier": qos_mult,
    }


# ---------------------------------------------------------------------------
# Position-dependent pricing (Section 9.2 — experimental)
# ---------------------------------------------------------------------------

def position_multiplier(
    position: int,
    window_size: int,
    beta: float = 0.3,
) -> float:
    """Compute position-dependent cost multiplier (experimental).

    From the whitepaper (Section 9.2):
        position_multiplier(pos, window_size) = (pos / window_size)^beta

    Tokens later in the context window cost more due to quadratic attention scaling.

    Args:
        position: Token's absolute position in context window.
        window_size: Total context window size.
        beta: Tuning parameter (suggested 0.1-0.5).

    Returns:
        Position multiplier (0.0 to 1.0).
    """
    if window_size <= 0 or position <= 0:
        return 0.0
    ratio = min(position / window_size, 1.0)
    return ratio ** beta


# ---------------------------------------------------------------------------
# QoS tier management
# ---------------------------------------------------------------------------

def qos_config_for_tier(tier: str) -> QoSConfig:
    """Get default QoS configuration for a given tier.

    Args:
        tier: QoSTier value.

    Returns:
        QoSConfig with tier-appropriate limits.
    """
    configs = {
        QoSTier.ECONOMY.value: QoSConfig(
            tier=QoSTier.ECONOMY.value,
            input_tokens_per_minute=500_000,
            output_tokens_per_minute=100_000,
            concurrent_interactions=5,
            max_request_size_tokens=200_000,
            max_context_utilization=0.60,
        ),
        QoSTier.STANDARD.value: QoSConfig(
            tier=QoSTier.STANDARD.value,
            input_tokens_per_minute=1_000_000,
            output_tokens_per_minute=200_000,
            concurrent_interactions=10,
            max_request_size_tokens=500_000,
            max_context_utilization=0.80,
        ),
        QoSTier.PRIORITY.value: QoSConfig(
            tier=QoSTier.PRIORITY.value,
            input_tokens_per_minute=2_000_000,
            output_tokens_per_minute=500_000,
            concurrent_interactions=20,
            max_request_size_tokens=800_000,
            max_context_utilization=0.90,
        ),
        QoSTier.RESERVED.value: QoSConfig(
            tier=QoSTier.RESERVED.value,
            input_tokens_per_minute=5_000_000,
            output_tokens_per_minute=1_000_000,
            concurrent_interactions=50,
            max_request_size_tokens=1_000_000,
            max_context_utilization=0.95,
        ),
    }
    return configs.get(tier, configs[QoSTier.STANDARD.value])


def check_qos_limits(
    config: QoSConfig,
    request_tokens: int,
    current_utilization: float,
) -> Dict[str, bool]:
    """Check whether a request fits within QoS limits.

    Args:
        config: QoS configuration.
        request_tokens: Size of the proposed request.
        current_utilization: Current context utilization.

    Returns:
        Dict with size_ok, utilization_ok, and overall allowed flag.
    """
    size_ok = request_tokens <= config.max_request_size_tokens
    util_ok = current_utilization <= config.max_context_utilization
    return {
        "size_ok": size_ok,
        "utilization_ok": util_ok,
        "allowed": size_ok and util_ok,
    }


# ---------------------------------------------------------------------------
# Back-pressure signaling (Section 10.4)
# ---------------------------------------------------------------------------

def generate_back_pressure(
    utilization: float,
    queue_depth: int = 0,
    estimated_queue_ms: int = 0,
) -> BackPressureSignal:
    """Generate a back-pressure signal based on current state.

    Args:
        utilization: Current context utilization (0.0 to 1.0).
        queue_depth: Number of economy-tier requests queued.
        estimated_queue_ms: Estimated wait time in milliseconds.

    Returns:
        BackPressureSignal.
    """
    level = congestion_level(utilization)

    if level == CongestionLevel.ABUNDANT.value:
        status = BackPressureStatus.OK.value
        available = [t.value for t in QoSTier]
    elif level in (CongestionLevel.MODERATE.value, CongestionLevel.HEAVY.value):
        status = BackPressureStatus.CONGESTED.value
        available = [QoSTier.STANDARD.value, QoSTier.PRIORITY.value, QoSTier.RESERVED.value]
    else:
        status = BackPressureStatus.OVERLOADED.value
        available = [QoSTier.PRIORITY.value, QoSTier.RESERVED.value]

    return BackPressureSignal(
        cwep_status=status,
        current_utilization=utilization,
        estimated_queue_time_ms=estimated_queue_ms,
        available_tiers=available,
        economy_queue_depth=queue_depth,
    )
