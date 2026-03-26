"""Tests for spam.py — deposits, reputation access, progressive sizing."""
from context_window_economics.spam import (
    calculate_deposit,
    check_access,
    classify_reputation,
    create_deposit,
    deposit_multiplier_for_tier,
    max_request_tokens,
    resolve_deposit,
)
from context_window_economics.schema import DepositStatus, ReputationTier


def test_classify_reputation():
    assert classify_reputation(90) == ReputationTier.HIGH.value
    assert classify_reputation(80.1) == ReputationTier.HIGH.value
    assert classify_reputation(60) == ReputationTier.MEDIUM.value
    assert classify_reputation(40.1) == ReputationTier.MEDIUM.value
    assert classify_reputation(20) == ReputationTier.LOW.value
    assert classify_reputation(0) == ReputationTier.LOW.value
    assert classify_reputation(-1) == ReputationTier.UNKNOWN.value


def test_deposit_multiplier_for_tier():
    assert deposit_multiplier_for_tier(ReputationTier.HIGH.value) == 0.0
    assert deposit_multiplier_for_tier(ReputationTier.MEDIUM.value) == 1.0
    assert deposit_multiplier_for_tier(ReputationTier.LOW.value) == 3.0
    assert deposit_multiplier_for_tier(ReputationTier.UNKNOWN.value) == 5.0


def test_calculate_deposit_high_rep():
    """High reputation agents pay no deposit."""
    amount, tier = calculate_deposit(
        estimated_request_tokens=100000,
        responder_input_rate_per_mtok=5.0,
        reputation_score=85,
    )
    assert amount == 0.0
    assert tier == ReputationTier.HIGH.value


def test_calculate_deposit_unknown():
    """Unknown agents pay maximum deposit (5x multiplier)."""
    amount, tier = calculate_deposit(
        estimated_request_tokens=100000,
        responder_input_rate_per_mtok=5.0,  # Opus input rate
        reputation_score=-1,
        base_multiplier=1.5,
    )
    # 100000 * 5.0/1M * 1.5 * 5.0 = 0.5 * 1.5 * 5.0 = 3.75
    assert abs(amount - 3.75) < 1e-6
    assert tier == ReputationTier.UNKNOWN.value


def test_calculate_deposit_medium():
    amount, tier = calculate_deposit(
        estimated_request_tokens=100000,
        responder_input_rate_per_mtok=5.0,
        reputation_score=60,
        base_multiplier=1.5,
    )
    # 100000 * 5.0/1M * 1.5 * 1.0 = 0.75
    assert abs(amount - 0.75) < 1e-6
    assert tier == ReputationTier.MEDIUM.value


def test_max_request_tokens_new_agent():
    assert max_request_tokens(reputation_score=10, interaction_count=2) == 1000


def test_max_request_tokens_building():
    assert max_request_tokens(reputation_score=30, interaction_count=10) == 10000


def test_max_request_tokens_established():
    assert max_request_tokens(reputation_score=50, interaction_count=50) == 100000


def test_max_request_tokens_unlimited():
    assert max_request_tokens(reputation_score=70, interaction_count=200) == -1


def test_check_access_allowed():
    allowed, reason = check_access(reputation_score=70, interaction_count=200, request_tokens=50000)
    assert allowed is True
    assert reason == "unlimited"


def test_check_access_denied():
    allowed, reason = check_access(reputation_score=10, interaction_count=2, request_tokens=5000)
    assert allowed is False
    assert "exceeds" in reason


def test_check_access_within_limits():
    allowed, reason = check_access(reputation_score=10, interaction_count=2, request_tokens=500)
    assert allowed is True
    assert reason == "within_limits"


def test_create_deposit():
    dep = create_deposit(
        requestor_id="req-1",
        responder_id="resp-1",
        estimated_request_tokens=50000,
        responder_input_rate_per_mtok=3.0,
        reputation_score=60,
    )
    assert dep.requestor_id == "req-1"
    assert dep.status == DepositStatus.COMMITTED.value
    assert dep.amount_usd > 0


def test_resolve_deposit_spam():
    dep = create_deposit("a", "b", 10000, 3.0, reputation_score=50)
    resolved = resolve_deposit(dep, is_spam=True)
    assert resolved.status == DepositStatus.FORFEITED.value


def test_resolve_deposit_legitimate():
    dep = create_deposit("a", "b", 10000, 3.0, reputation_score=50)
    resolved = resolve_deposit(dep, is_spam=False)
    assert resolved.status == DepositStatus.REFUNDED.value
