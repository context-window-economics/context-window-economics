"""Settlement engine for bilateral agent cost allocation.

Handles CMR verification, settlement proposal generation, settlement batching,
and provides the payment-rail abstraction interface (Section 13.2).
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .allocation import allocate
from .schema import (
    AllocationMethod,
    CostMeteringRecord,
    DEFAULT_BATCH_THRESHOLD_USD,
    DEFAULT_BATCH_WINDOW_SECONDS,
    DEFAULT_SETTLEMENT_THRESHOLD,
    SettlementProposal,
    SettlementTier,
)


# ---------------------------------------------------------------------------
# Payment rail abstraction (Section 13.2)
# ---------------------------------------------------------------------------

class PaymentRail:
    """Abstract payment rail interface.

    Concrete implementations wrap x402, MPP, L402, Superfluid, or custom rails.
    The default implementation is a no-op ledger for metering-only deployments.
    """

    def commit_deposit(self, amount_usd: float, escrow_id: str) -> bool:
        """Lock funds in escrow."""
        return True

    def release_deposit(self, escrow_id: str, to_agent: str) -> bool:
        """Release escrowed funds to the specified agent."""
        return True

    def forfeit_deposit(self, escrow_id: str) -> bool:
        """Forfeit escrowed funds (spam penalty)."""
        return True

    def settle(
        self,
        from_agent: str,
        to_agent: str,
        amount_usd: float,
        interaction_id: str,
    ) -> "SettlementReceipt":
        """Execute a one-time settlement payment."""
        return SettlementReceipt(
            interaction_id=interaction_id,
            from_agent=from_agent,
            to_agent=to_agent,
            amount_usd=amount_usd,
            status="completed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def stream_open(
        self,
        from_agent: str,
        to_agent: str,
        rate_usd_per_second: float,
    ) -> str:
        """Open a streaming payment channel. Returns a stream handle."""
        return f"stream-{from_agent}-{to_agent}"

    def stream_close(self, handle: str) -> "SettlementReceipt":
        """Close a streaming payment channel."""
        return SettlementReceipt(
            interaction_id=handle,
            from_agent="",
            to_agent="",
            amount_usd=0.0,
            status="closed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


@dataclass
class SettlementReceipt:
    """Receipt from a completed settlement."""
    interaction_id: str = ""
    from_agent: str = ""
    to_agent: str = ""
    amount_usd: float = 0.0
    status: str = "completed"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tx_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "amount_usd": self.amount_usd,
            "status": self.status,
            "timestamp": self.timestamp,
            "tx_ref": self.tx_ref,
        }


# ---------------------------------------------------------------------------
# Settlement Engine
# ---------------------------------------------------------------------------

class SettlementEngine:
    """Core settlement engine that evaluates CMRs and produces settlement proposals.

    Supports all three CWEP tiers:
      - Tier 1: Metering only (no settlement)
      - Tier 2: Rule-based (static allocation rules)
      - Tier 3: Dynamic (Shapley/Nash)
    """

    def __init__(
        self,
        tier: str = SettlementTier.TIER_1_METERING.value,
        method: str = AllocationMethod.SHAPLEY.value,
        threshold_usd: float = DEFAULT_SETTLEMENT_THRESHOLD,
        payment_rail: Optional[PaymentRail] = None,
        tolerance: float = 0.05,
        **allocation_kwargs,
    ):
        """
        Args:
            tier: Settlement tier.
            method: Default allocation method for Tier 2/3.
            threshold_usd: Minimum cost to trigger settlement.
            payment_rail: Payment rail implementation (default: no-op).
            tolerance: Agreement tolerance as fraction of total cost (default 5%).
            **allocation_kwargs: Extra params passed to allocation methods.
        """
        self.tier = tier
        self.method = method
        self.threshold_usd = threshold_usd
        self.payment_rail = payment_rail or PaymentRail()
        self.tolerance = tolerance
        self.allocation_kwargs = allocation_kwargs

    def propose(self, cmr: CostMeteringRecord) -> Optional[SettlementProposal]:
        """Generate a settlement proposal for the given CMR.

        Returns None for Tier 1 or if total cost is below threshold.
        """
        if self.tier == SettlementTier.TIER_1_METERING.value:
            return None

        if cmr.totals.total_cost_usd < self.threshold_usd:
            return None

        return allocate(cmr, method=self.method, **self.allocation_kwargs)

    def settle(
        self, cmr: CostMeteringRecord, proposal: Optional[SettlementProposal] = None
    ) -> Optional[SettlementReceipt]:
        """Execute settlement for a CMR.

        If no proposal is provided, one is generated. If the proposal's net
        transfer is zero or below threshold, no payment is executed.
        """
        if proposal is None:
            proposal = self.propose(cmr)
        if proposal is None:
            return None

        if proposal.net_transfer_usd < self.threshold_usd:
            return None

        # Attach proposal to CMR
        cmr.settlement = proposal

        # Determine from/to
        if proposal.transfer_direction == "requestor_to_responder":
            from_agent = cmr.requestor.agent_id if cmr.requestor else ""
            to_agent = cmr.responder.agent_id if cmr.responder else ""
        else:
            from_agent = cmr.responder.agent_id if cmr.responder else ""
            to_agent = cmr.requestor.agent_id if cmr.requestor else ""

        return self.payment_rail.settle(
            from_agent=from_agent,
            to_agent=to_agent,
            amount_usd=proposal.net_transfer_usd,
            interaction_id=cmr.interaction_id,
        )

    def verify_proposals(
        self,
        proposal_a: SettlementProposal,
        proposal_b: SettlementProposal,
        total_cost: float,
    ) -> Tuple[bool, float]:
        """Verify two agents' settlement proposals agree within tolerance.

        Returns (agreed: bool, discrepancy: float).
        """
        discrepancy = abs(
            proposal_a.requestor_pays_usd - proposal_b.requestor_pays_usd
        )
        threshold = total_cost * self.tolerance
        return discrepancy <= threshold, discrepancy


# ---------------------------------------------------------------------------
# Settlement Batching (Section 13.3)
# ---------------------------------------------------------------------------

class SettlementBatch:
    """Accumulates CMRs and computes net settlement across a batch window.

    Reduces transaction fees by settling the net amount across many interactions.
    """

    def __init__(
        self,
        window_seconds: int = DEFAULT_BATCH_WINDOW_SECONDS,
        threshold_usd: float = DEFAULT_BATCH_THRESHOLD_USD,
        method: str = AllocationMethod.SHAPLEY.value,
        **allocation_kwargs,
    ):
        self.window_seconds = window_seconds
        self.threshold_usd = threshold_usd
        self.method = method
        self.allocation_kwargs = allocation_kwargs
        self._cmrs: List[CostMeteringRecord] = []
        self._started: Optional[datetime] = None

    def add(self, cmr: CostMeteringRecord) -> None:
        """Add a CMR to the current batch."""
        if self._started is None:
            self._started = datetime.now(timezone.utc)
        self._cmrs.append(cmr)

    @property
    def count(self) -> int:
        return len(self._cmrs)

    def should_flush(self) -> bool:
        """Check if the batch should be flushed (time or $ threshold)."""
        if not self._cmrs:
            return False

        # Check time window
        if self._started is not None:
            elapsed = (datetime.now(timezone.utc) - self._started).total_seconds()
            if elapsed >= self.window_seconds:
                return True

        # Check net amount threshold
        net = self._compute_net()
        return abs(net) >= self.threshold_usd

    def flush(self) -> Dict[str, Any]:
        """Compute net settlement for the batch and reset.

        Returns:
            Dict with agent_pair, net_amount, direction, interaction_count, cmr_ids.
        """
        if not self._cmrs:
            return {
                "net_amount_usd": 0.0,
                "direction": "",
                "interaction_count": 0,
                "cmr_ids": [],
            }

        net = self._compute_net()
        cmr_ids = [c.interaction_id for c in self._cmrs]
        count = len(self._cmrs)

        if net >= 0:
            direction = "requestor_to_responder"
        else:
            direction = "responder_to_requestor"
            net = -net

        result = {
            "net_amount_usd": net,
            "direction": direction,
            "interaction_count": count,
            "cmr_ids": cmr_ids,
        }

        # Reset
        self._cmrs = []
        self._started = None
        return result

    def _compute_net(self) -> float:
        """Compute net transfer across all CMRs in the batch.

        Positive = requestor owes responder.
        """
        total_net = 0.0
        for cmr in self._cmrs:
            proposal = allocate(cmr, method=self.method, **self.allocation_kwargs)
            if proposal.transfer_direction == "requestor_to_responder":
                total_net += proposal.net_transfer_usd
            else:
                total_net -= proposal.net_transfer_usd
        return total_net


# ---------------------------------------------------------------------------
# CMR verification utilities
# ---------------------------------------------------------------------------

def cmr_hash(cmr: CostMeteringRecord) -> str:
    """Compute SHA-256 hash of a CMR for verification/exchange."""
    data = json.dumps(cmr.to_dict(), sort_keys=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_cmr_pair(cmr_a: CostMeteringRecord, cmr_b: CostMeteringRecord) -> bool:
    """Verify that two independently generated CMRs describe the same interaction.

    Checks interaction_id and token flow agreement.
    """
    if cmr_a.interaction_id != cmr_b.interaction_id:
        return False

    for flow_key in cmr_a.flows:
        if flow_key not in cmr_b.flows:
            return False
        if cmr_a.flows[flow_key].tokens != cmr_b.flows[flow_key].tokens:
            return False
    return True
