"""Tests for settlement.py — settlement engine, batching, verification."""
from context_window_economics.metering import Meter
from context_window_economics.settlement import (
    PaymentRail,
    SettlementBatch,
    SettlementEngine,
    SettlementReceipt,
    cmr_hash,
    verify_cmr_pair,
)
from context_window_economics.schema import AllocationMethod, SettlementTier


def _make_cmr():
    meter = Meter(agent_id="agent-a", model="claude-sonnet-4-6", provider="anthropic")
    return meter.record_interaction(
        responder_id="agent-b",
        request_tokens=10000,
        response_tokens=3000,
    )


def test_tier1_no_settlement():
    engine = SettlementEngine(tier=SettlementTier.TIER_1_METERING.value)
    cmr = _make_cmr()
    proposal = engine.propose(cmr)
    assert proposal is None


def test_tier2_rule_based():
    engine = SettlementEngine(
        tier=SettlementTier.TIER_2_RULE_BASED.value,
        method=AllocationMethod.EQUAL_SPLIT.value,
    )
    cmr = _make_cmr()
    proposal = engine.propose(cmr)
    assert proposal is not None
    assert proposal.method == "equal_split"


def test_tier3_dynamic_shapley():
    engine = SettlementEngine(
        tier=SettlementTier.TIER_3_DYNAMIC.value,
        method=AllocationMethod.SHAPLEY.value,
    )
    cmr = _make_cmr()
    proposal = engine.propose(cmr)
    assert proposal is not None
    assert proposal.method == "shapley"
    assert abs(proposal.requestor_pays_usd - 0.192) < 1e-6


def test_below_threshold_no_settlement():
    engine = SettlementEngine(
        tier=SettlementTier.TIER_2_RULE_BASED.value,
        threshold_usd=1.0,  # Higher than any single interaction
    )
    cmr = _make_cmr()
    proposal = engine.propose(cmr)
    assert proposal is None


def test_settle_executes_payment():
    engine = SettlementEngine(
        tier=SettlementTier.TIER_3_DYNAMIC.value,
        method=AllocationMethod.SHAPLEY.value,
    )
    cmr = _make_cmr()
    receipt = engine.settle(cmr)
    assert receipt is not None
    assert receipt.status == "completed"
    assert receipt.amount_usd > 0


def test_verify_proposals_agree():
    engine = SettlementEngine()
    from context_window_economics.schema import SettlementProposal
    p1 = SettlementProposal(requestor_pays_usd=0.192, responder_pays_usd=0.042)
    p2 = SettlementProposal(requestor_pays_usd=0.192, responder_pays_usd=0.042)
    agreed, disc = engine.verify_proposals(p1, p2, total_cost=0.234)
    assert agreed is True
    assert disc < 1e-9


def test_verify_proposals_disagree():
    engine = SettlementEngine(tolerance=0.05)
    from context_window_economics.schema import SettlementProposal
    p1 = SettlementProposal(requestor_pays_usd=0.192)
    p2 = SettlementProposal(requestor_pays_usd=0.150)
    agreed, disc = engine.verify_proposals(p1, p2, total_cost=0.234)
    assert agreed is False


def test_cmr_hash_deterministic():
    cmr = _make_cmr()
    h1 = cmr_hash(cmr)
    h2 = cmr_hash(cmr)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_verify_cmr_pair():
    cmr1 = _make_cmr()
    cmr2 = _make_cmr()
    cmr2.interaction_id = cmr1.interaction_id
    # Same flows
    for k in cmr1.flows:
        cmr2.flows[k].tokens = cmr1.flows[k].tokens
    assert verify_cmr_pair(cmr1, cmr2) is True


def test_verify_cmr_pair_mismatch():
    cmr1 = _make_cmr()
    cmr2 = _make_cmr()
    # Different interaction IDs
    assert verify_cmr_pair(cmr1, cmr2) is False


def test_settlement_batch():
    batch = SettlementBatch(threshold_usd=0.50)
    assert batch.count == 0

    meter = Meter(agent_id="a", model="claude-sonnet-4-6", provider="anthropic")
    for _ in range(5):
        cmr = meter.record_interaction(
            responder_id="b", request_tokens=10000, response_tokens=3000,
        )
        batch.add(cmr)

    assert batch.count == 5

    result = batch.flush()
    assert result["interaction_count"] == 5
    assert result["net_amount_usd"] > 0
    assert len(result["cmr_ids"]) == 5
    assert batch.count == 0  # Reset after flush


def test_payment_rail_default():
    rail = PaymentRail()
    receipt = rail.settle("a", "b", 0.10, "test-id")
    assert receipt.status == "completed"
    assert receipt.amount_usd == 0.10

    handle = rail.stream_open("a", "b", 0.001)
    assert "stream" in handle
    close_receipt = rail.stream_close(handle)
    assert close_receipt.status == "closed"
