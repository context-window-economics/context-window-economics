"""Data structures, constants, and JSON schemas for the Context Window Economics Protocol.

Implements the CWEP specification from the whitepaper: CMR (Cost Metering Record),
agent pricing, settlement proposals, deposit records, QoS tiers, and back-pressure signals.
"""
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"

# Provider pricing per MTok (USD) — defaults as of March 2026
DEFAULT_PROVIDER_PRICING = {
    "anthropic": {
        "claude-opus-4-6":   {"input": 5.00,  "output": 25.00, "cache_hit": 0.50},
        "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00, "cache_hit": 0.30},
        "claude-haiku-4-5":  {"input": 0.25,  "output": 1.25,  "cache_hit": 0.025},
    },
    "openai": {
        "gpt-4.1":      {"input": 2.00,  "output": 8.00,  "cache_hit": 0.50},
        "gpt-4.1-mini": {"input": 0.40,  "output": 1.60,  "cache_hit": 0.10},
        "o3":           {"input": 2.00,  "output": 8.00,  "cache_hit": 0.50},
    },
    "google": {
        "gemini-2.5-pro": {"input": 1.25, "output": 10.00, "cache_hit": 0.3125},
    },
}

# Settlement threshold (USD) — interactions below this are not settled
DEFAULT_SETTLEMENT_THRESHOLD = 0.01

# Deposit multiplier for spam prevention
DEFAULT_DEPOSIT_MULTIPLIER = 1.5

# CMR batch defaults
DEFAULT_BATCH_WINDOW_SECONDS = 3600  # 1 hour
DEFAULT_BATCH_THRESHOLD_USD = 1.00

# Max CMR size (bytes)
MAX_CMR_SIZE_BYTES = 2048

# Protocol overhead target (tokens)
PROTOCOL_OVERHEAD_TOKENS = 500


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CostFlow(str, Enum):
    """The four cost flows in every agent interaction."""
    REQUEST_OUTPUT = "request_output"   # RO: requestor generates request
    REQUEST_INPUT = "request_input"     # RI: responder processes request
    RESPONSE_OUTPUT = "response_output" # SO: responder generates response
    RESPONSE_INPUT = "response_input"   # SI: requestor processes response


class AllocationMethod(str, Enum):
    """Cost allocation methods."""
    REQUESTOR_PAYS = "requestor_pays"
    RESPONDER_PAYS = "responder_pays"
    EQUAL_SPLIT = "equal_split"
    PROPORTIONAL = "proportional"
    BENEFICIARY_PAYS = "beneficiary_pays"
    SHAPLEY = "shapley"
    NASH_BARGAINING = "nash_bargaining"


class SettlementTier(str, Enum):
    """CWEP settlement tiers."""
    TIER_1_METERING = "tier_1_metering"       # No settlement, metering only
    TIER_2_RULE_BASED = "tier_2_rule_based"   # Static allocation rules
    TIER_3_DYNAMIC = "tier_3_dynamic"         # Real-time Shapley/Nash


class QoSTier(str, Enum):
    """Quality-of-Service tiers."""
    ECONOMY = "economy"
    STANDARD = "standard"
    PRIORITY = "priority"
    RESERVED = "reserved"


class CongestionLevel(str, Enum):
    """Context utilization congestion levels."""
    ABUNDANT = "abundant"     # < 50%
    MODERATE = "moderate"     # 50-80%
    HEAVY = "heavy"           # 80-95%
    CRITICAL = "critical"     # >= 95%


class ReputationTier(str, Enum):
    """Reputation-weighted access tiers for spam prevention."""
    HIGH = "high"         # >80/100 — no deposit
    MEDIUM = "medium"     # 40-80 — standard deposit
    LOW = "low"           # <40 — elevated deposit (3x)
    UNKNOWN = "unknown"   # No reputation — max deposit (5x)


class DepositStatus(str, Enum):
    """Deposit lifecycle states."""
    COMMITTED = "committed"
    REFUNDED = "refunded"
    FORFEITED = "forfeited"
    DISPUTED = "disputed"


class BackPressureStatus(str, Enum):
    """Back-pressure signal statuses."""
    OK = "ok"
    CONGESTED = "congested"
    OVERLOADED = "overloaded"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AgentPricing:
    """Per-token pricing for an agent's LLM provider."""
    input_rate_per_mtok: float
    output_rate_per_mtok: float
    cache_hit_rate_per_mtok: float = 0.0
    currency: str = "USD"

    def input_cost(self, tokens: int, cached_tokens: int = 0) -> float:
        """Compute input cost for given token counts."""
        regular = tokens - cached_tokens
        return (regular * self.input_rate_per_mtok / 1_000_000
                + cached_tokens * self.cache_hit_rate_per_mtok / 1_000_000)

    def output_cost(self, tokens: int) -> float:
        """Compute output cost for given token count."""
        return tokens * self.output_rate_per_mtok / 1_000_000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPricing":
        return cls(**data)

    @classmethod
    def from_provider(cls, provider: str, model: str) -> "AgentPricing":
        """Create pricing from known provider defaults."""
        providers = DEFAULT_PROVIDER_PRICING.get(provider, {})
        rates = providers.get(model)
        if rates is None:
            raise ValueError(f"Unknown provider/model: {provider}/{model}")
        return cls(
            input_rate_per_mtok=rates["input"],
            output_rate_per_mtok=rates["output"],
            cache_hit_rate_per_mtok=rates.get("cache_hit", 0.0),
        )


@dataclass
class AgentInfo:
    """Identity and pricing info for an agent in an interaction."""
    agent_id: str
    model: str
    provider: str
    pricing: AgentPricing

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pricing"] = self.pricing.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        pricing = AgentPricing.from_dict(data["pricing"])
        return cls(
            agent_id=data["agent_id"],
            model=data["model"],
            provider=data["provider"],
            pricing=pricing,
        )


@dataclass
class TokenFlow:
    """A single directional token flow in an interaction."""
    tokens: int
    cached_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenFlow":
        return cls(**data)


@dataclass
class InteractionTotals:
    """Aggregate cost totals for an interaction."""
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    requestor_incurred_usd: float = 0.0
    responder_incurred_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionTotals":
        return cls(**data)


@dataclass
class ContextState:
    """Context window state at time of interaction."""
    responder_utilization_pre: float = 0.0
    responder_utilization_post: float = 0.0
    responder_window_size: int = 1_000_000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextState":
        return cls(**data)


@dataclass
class SettlementProposal:
    """A cost allocation proposal from the settlement engine."""
    method: str = ""
    requestor_pays_usd: float = 0.0
    responder_pays_usd: float = 0.0
    net_transfer_usd: float = 0.0
    transfer_direction: str = ""  # "requestor_to_responder" or "responder_to_requestor"
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettlementProposal":
        return cls(**data)


@dataclass
class CostMeteringRecord:
    """CWEP Cost Metering Record (CMR) — the core data structure.

    Captures all four token flows, agent pricing, context state,
    and optional settlement data for a single agent interaction.
    """
    cwep_version: str = PROTOCOL_VERSION
    interaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    requestor: Optional[AgentInfo] = None
    responder: Optional[AgentInfo] = None
    flows: Dict[str, TokenFlow] = field(default_factory=lambda: {
        CostFlow.REQUEST_OUTPUT.value: TokenFlow(0),
        CostFlow.REQUEST_INPUT.value: TokenFlow(0),
        CostFlow.RESPONSE_OUTPUT.value: TokenFlow(0),
        CostFlow.RESPONSE_INPUT.value: TokenFlow(0),
    })
    totals: InteractionTotals = field(default_factory=InteractionTotals)
    context_state: ContextState = field(default_factory=ContextState)
    coc_chain_ref: Optional[str] = None
    settlement: Optional[SettlementProposal] = None

    def compute_costs(self) -> None:
        """Recompute flow costs and totals from token counts and pricing."""
        if self.requestor is None or self.responder is None:
            return

        rp = self.requestor.pricing
        sp = self.responder.pricing

        ro = self.flows[CostFlow.REQUEST_OUTPUT.value]
        ri = self.flows[CostFlow.REQUEST_INPUT.value]
        so = self.flows[CostFlow.RESPONSE_OUTPUT.value]
        si = self.flows[CostFlow.RESPONSE_INPUT.value]

        ro.cost_usd = rp.output_cost(ro.tokens)
        ri.cost_usd = sp.input_cost(ri.tokens, ri.cached_tokens)
        so.cost_usd = sp.output_cost(so.tokens)
        si.cost_usd = rp.input_cost(si.tokens, si.cached_tokens)

        self.totals.total_tokens = ro.tokens + ri.tokens + so.tokens + si.tokens
        self.totals.total_cost_usd = ro.cost_usd + ri.cost_usd + so.cost_usd + si.cost_usd
        self.totals.requestor_incurred_usd = ro.cost_usd + si.cost_usd
        self.totals.responder_incurred_usd = ri.cost_usd + so.cost_usd

    def to_dict(self) -> Dict[str, Any]:
        flows_dict = {k: v.to_dict() for k, v in self.flows.items()}
        return {
            "cwep_version": self.cwep_version,
            "interaction_id": self.interaction_id,
            "timestamp": self.timestamp,
            "requestor": self.requestor.to_dict() if self.requestor else None,
            "responder": self.responder.to_dict() if self.responder else None,
            "flows": flows_dict,
            "totals": self.totals.to_dict(),
            "context_state": self.context_state.to_dict(),
            "coc_chain_ref": self.coc_chain_ref,
            "settlement": self.settlement.to_dict() if self.settlement else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostMeteringRecord":
        requestor = AgentInfo.from_dict(data["requestor"]) if data.get("requestor") else None
        responder = AgentInfo.from_dict(data["responder"]) if data.get("responder") else None
        flows = {k: TokenFlow.from_dict(v) for k, v in data.get("flows", {}).items()}
        totals = InteractionTotals.from_dict(data.get("totals", {}))
        context_state = ContextState.from_dict(data.get("context_state", {}))
        settlement = SettlementProposal.from_dict(data["settlement"]) if data.get("settlement") else None
        return cls(
            cwep_version=data.get("cwep_version", PROTOCOL_VERSION),
            interaction_id=data.get("interaction_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", ""),
            requestor=requestor,
            responder=responder,
            flows=flows,
            totals=totals,
            context_state=context_state,
            coc_chain_ref=data.get("coc_chain_ref"),
            settlement=settlement,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "CostMeteringRecord":
        return cls.from_dict(json.loads(json_str))


@dataclass
class DepositRecord:
    """Record of a spam-prevention deposit."""
    deposit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requestor_id: str = ""
    responder_id: str = ""
    amount_usd: float = 0.0
    status: str = DepositStatus.COMMITTED.value
    interaction_id: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    multiplier: float = DEFAULT_DEPOSIT_MULTIPLIER
    reputation_tier: str = ReputationTier.UNKNOWN.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DepositRecord":
        return cls(**data)


@dataclass
class QoSConfig:
    """Quality-of-Service configuration for an agent."""
    tier: str = QoSTier.STANDARD.value
    input_tokens_per_minute: int = 1_000_000
    output_tokens_per_minute: int = 200_000
    concurrent_interactions: int = 10
    max_request_size_tokens: int = 500_000
    max_context_utilization: float = 0.80

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QoSConfig":
        return cls(**data)


@dataclass
class BackPressureSignal:
    """Back-pressure signal sent when an agent approaches capacity limits."""
    cwep_status: str = BackPressureStatus.OK.value
    current_utilization: float = 0.0
    estimated_queue_time_ms: int = 0
    available_tiers: List[str] = field(default_factory=lambda: [
        QoSTier.ECONOMY.value, QoSTier.STANDARD.value,
        QoSTier.PRIORITY.value, QoSTier.RESERVED.value,
    ])
    economy_queue_depth: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackPressureSignal":
        return cls(**data)


@dataclass
class ContextReservation:
    """A context window capacity reservation."""
    reservation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requestor_id: str = ""
    responder_id: str = ""
    capacity_tokens: int = 100_000
    duration_seconds: int = 3600
    price_usd: float = 0.0
    qos_tier: str = QoSTier.RESERVED.value
    auto_renew: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextReservation":
        return cls(**data)


# ---------------------------------------------------------------------------
# QoS tier rate multipliers
# ---------------------------------------------------------------------------

QOS_RATE_MULTIPLIERS = {
    QoSTier.ECONOMY.value: 1.0,
    QoSTier.STANDARD.value: 1.0,
    QoSTier.PRIORITY.value: 2.0,
    QoSTier.RESERVED.value: 3.0,
}

# ---------------------------------------------------------------------------
# Reputation tier deposit multipliers
# ---------------------------------------------------------------------------

REPUTATION_DEPOSIT_MULTIPLIERS = {
    ReputationTier.HIGH.value: 0.0,      # No deposit required
    ReputationTier.MEDIUM.value: 1.0,    # Standard deposit
    ReputationTier.LOW.value: 3.0,       # Elevated deposit
    ReputationTier.UNKNOWN.value: 5.0,   # Maximum deposit
}

# Reputation score thresholds
REPUTATION_THRESHOLDS = {
    ReputationTier.HIGH.value: 80,
    ReputationTier.MEDIUM.value: 40,
    ReputationTier.LOW.value: 0,
}

# Progressive request size limits
PROGRESSIVE_REQUEST_LIMITS = [
    {"max_reputation": 20, "max_interactions": 5, "max_tokens": 1_000},
    {"max_reputation": 40, "max_interactions": 20, "max_tokens": 10_000},
    {"max_reputation": 60, "max_interactions": 100, "max_tokens": 100_000},
]
