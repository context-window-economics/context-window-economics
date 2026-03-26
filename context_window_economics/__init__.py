"""Context Window Economics Protocol (CWEP).

Bilateral cost allocation, context pricing, and resource markets
for autonomous agent interactions.

Part of the AB Support Trust Ecosystem — Layer 4 (Market/Economics).

    from context_window_economics import Meter, allocate, SettlementEngine
    meter = Meter(agent_id="did:example:my-agent")
    cmr = meter.record_interaction(
        responder_id="did:example:other",
        request_tokens=10000,
        response_tokens=3000,
    )
    proposal = allocate(cmr, method="shapley")
"""

__version__ = "0.1.0"

# --- Schema: data structures, constants, enums ---
from .schema import (
    # Constants
    DEFAULT_BATCH_THRESHOLD_USD,
    DEFAULT_BATCH_WINDOW_SECONDS,
    DEFAULT_DEPOSIT_MULTIPLIER,
    DEFAULT_PROVIDER_PRICING,
    DEFAULT_SETTLEMENT_THRESHOLD,
    MAX_CMR_SIZE_BYTES,
    PROGRESSIVE_REQUEST_LIMITS,
    PROTOCOL_OVERHEAD_TOKENS,
    PROTOCOL_VERSION,
    QOS_RATE_MULTIPLIERS,
    REPUTATION_DEPOSIT_MULTIPLIERS,
    REPUTATION_THRESHOLDS,
    SCHEMA_VERSION,
    # Enums
    AllocationMethod,
    BackPressureStatus,
    CongestionLevel,
    CostFlow,
    DepositStatus,
    QoSTier,
    ReputationTier,
    SettlementTier,
    # Data structures
    AgentInfo,
    AgentPricing,
    BackPressureSignal,
    ContextReservation,
    ContextState,
    CostMeteringRecord,
    DepositRecord,
    InteractionTotals,
    QoSConfig,
    SettlementProposal,
    TokenFlow,
)

# --- Metering ---
from .metering import (
    Meter,
    compute_flow_cost,
    estimate_interaction_cost,
)

# --- Allocation ---
from .allocation import (
    allocate,
    allocate_equal_split,
    allocate_nash,
    allocate_proportional,
    allocate_requestor_pays,
    allocate_responder_pays,
    allocate_shapley,
)

# --- Settlement ---
from .settlement import (
    PaymentRail,
    SettlementBatch,
    SettlementEngine,
    SettlementReceipt,
    cmr_hash,
    verify_cmr_pair,
)

# --- Spam prevention ---
from .spam import (
    calculate_deposit,
    check_access,
    classify_reputation,
    create_deposit,
    deposit_multiplier_for_tier,
    max_request_tokens,
    resolve_deposit,
)

# --- Congestion pricing ---
from .congestion import (
    check_qos_limits,
    congestion_level,
    congestion_multiplier,
    effective_token_price,
    generate_back_pressure,
    position_multiplier,
    qos_config_for_tier,
)

# --- Caching economics ---
from .caching import (
    CacheTracker,
    cache_amortized_cost,
    compression_roi,
    memory_vs_context_crossover,
)

# --- Store ---
from .store import CWEPStore

__all__ = [
    # Version
    "__version__",
    # Constants
    "DEFAULT_BATCH_THRESHOLD_USD",
    "DEFAULT_BATCH_WINDOW_SECONDS",
    "DEFAULT_DEPOSIT_MULTIPLIER",
    "DEFAULT_PROVIDER_PRICING",
    "DEFAULT_SETTLEMENT_THRESHOLD",
    "MAX_CMR_SIZE_BYTES",
    "PROGRESSIVE_REQUEST_LIMITS",
    "PROTOCOL_OVERHEAD_TOKENS",
    "PROTOCOL_VERSION",
    "QOS_RATE_MULTIPLIERS",
    "REPUTATION_DEPOSIT_MULTIPLIERS",
    "REPUTATION_THRESHOLDS",
    "SCHEMA_VERSION",
    # Enums
    "AllocationMethod",
    "BackPressureStatus",
    "CongestionLevel",
    "CostFlow",
    "DepositStatus",
    "QoSTier",
    "ReputationTier",
    "SettlementTier",
    # Data structures
    "AgentInfo",
    "AgentPricing",
    "BackPressureSignal",
    "ContextReservation",
    "ContextState",
    "CostMeteringRecord",
    "DepositRecord",
    "InteractionTotals",
    "QoSConfig",
    "SettlementProposal",
    "TokenFlow",
    # Metering
    "Meter",
    "compute_flow_cost",
    "estimate_interaction_cost",
    # Allocation
    "allocate",
    "allocate_equal_split",
    "allocate_nash",
    "allocate_proportional",
    "allocate_requestor_pays",
    "allocate_responder_pays",
    "allocate_shapley",
    # Settlement
    "PaymentRail",
    "SettlementBatch",
    "SettlementEngine",
    "SettlementReceipt",
    "cmr_hash",
    "verify_cmr_pair",
    # Spam
    "calculate_deposit",
    "check_access",
    "classify_reputation",
    "create_deposit",
    "deposit_multiplier_for_tier",
    "max_request_tokens",
    "resolve_deposit",
    # Congestion
    "check_qos_limits",
    "congestion_level",
    "congestion_multiplier",
    "effective_token_price",
    "generate_back_pressure",
    "position_multiplier",
    "qos_config_for_tier",
    # Caching
    "CacheTracker",
    "cache_amortized_cost",
    "compression_roi",
    "memory_vs_context_crossover",
    # Store
    "CWEPStore",
]
