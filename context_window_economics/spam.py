"""Spam prevention via deposits, reputation-weighted access, and progressive request sizing.

Implements Section 11 of the CWEP whitepaper: deposit calculation, reputation-based
access tiers, deposit scaling for unknown agents, and progressive token limits.
"""
from typing import Optional, Tuple

from .schema import (
    DEFAULT_DEPOSIT_MULTIPLIER,
    DepositRecord,
    DepositStatus,
    PROGRESSIVE_REQUEST_LIMITS,
    REPUTATION_DEPOSIT_MULTIPLIERS,
    REPUTATION_THRESHOLDS,
    ReputationTier,
)


def classify_reputation(score: float) -> str:
    """Map a 0-100 reputation score to a ReputationTier.

    Args:
        score: ARP reputation score (0-100).

    Returns:
        ReputationTier value string.
    """
    if score > REPUTATION_THRESHOLDS[ReputationTier.HIGH.value]:
        return ReputationTier.HIGH.value
    elif score > REPUTATION_THRESHOLDS[ReputationTier.MEDIUM.value]:
        return ReputationTier.MEDIUM.value
    elif score >= 0:
        return ReputationTier.LOW.value
    return ReputationTier.UNKNOWN.value


def deposit_multiplier_for_tier(tier: str) -> float:
    """Get the deposit multiplier for a reputation tier.

    Returns:
        Multiplier (0.0 for high rep, 5.0 for unknown).
    """
    return REPUTATION_DEPOSIT_MULTIPLIERS.get(tier, DEFAULT_DEPOSIT_MULTIPLIER)


def calculate_deposit(
    estimated_request_tokens: int,
    responder_input_rate_per_mtok: float,
    reputation_score: float = -1.0,
    base_multiplier: float = DEFAULT_DEPOSIT_MULTIPLIER,
) -> Tuple[float, str]:
    """Calculate the required deposit for a request.

    From the whitepaper (Section 11.2):
        deposit_amount = estimated_request_tokens * responder_input_rate * deposit_multiplier

    The deposit_multiplier is further scaled by reputation tier.

    Args:
        estimated_request_tokens: Expected token count for the request.
        responder_input_rate_per_mtok: Responder's input rate per MTok.
        reputation_score: Requestor's ARP reputation score (0-100), or -1 for unknown.
        base_multiplier: Base deposit multiplier set by responder.

    Returns:
        (deposit_amount_usd, reputation_tier)
    """
    if reputation_score < 0:
        tier = ReputationTier.UNKNOWN.value
    else:
        tier = classify_reputation(reputation_score)

    rep_multiplier = deposit_multiplier_for_tier(tier)

    if rep_multiplier == 0.0:
        return 0.0, tier

    # Base processing cost
    processing_cost = estimated_request_tokens * responder_input_rate_per_mtok / 1_000_000
    deposit = processing_cost * base_multiplier * rep_multiplier

    return deposit, tier


def max_request_tokens(reputation_score: float, interaction_count: int) -> int:
    """Determine maximum allowed request size based on reputation and history.

    From the whitepaper (Section 11.4):
        Progressive request sizing prevents context-flooding attacks.

    Args:
        reputation_score: ARP score (0-100).
        interaction_count: Number of prior interactions.

    Returns:
        Maximum allowed request tokens. Returns -1 for unlimited.
    """
    for level in PROGRESSIVE_REQUEST_LIMITS:
        if (reputation_score < level["max_reputation"]
                and interaction_count < level["max_interactions"]):
            return level["max_tokens"]
    return -1  # Unlimited


def check_access(
    reputation_score: float,
    interaction_count: int,
    request_tokens: int,
) -> Tuple[bool, str]:
    """Check whether a request should be allowed based on spam prevention rules.

    Args:
        reputation_score: ARP score (0-100).
        interaction_count: Number of prior interactions with this responder.
        request_tokens: Size of the proposed request.

    Returns:
        (allowed: bool, reason: str)
    """
    limit = max_request_tokens(reputation_score, interaction_count)
    if limit == -1:
        return True, "unlimited"

    if request_tokens > limit:
        return False, (
            f"Request size {request_tokens} exceeds progressive limit "
            f"{limit} for reputation={reputation_score:.0f}, "
            f"interactions={interaction_count}"
        )
    return True, "within_limits"


def create_deposit(
    requestor_id: str,
    responder_id: str,
    estimated_request_tokens: int,
    responder_input_rate_per_mtok: float,
    reputation_score: float = -1.0,
    base_multiplier: float = DEFAULT_DEPOSIT_MULTIPLIER,
    interaction_id: Optional[str] = None,
) -> DepositRecord:
    """Create a deposit record for an upcoming interaction.

    Args:
        requestor_id: Requesting agent's ID.
        responder_id: Responding agent's ID.
        estimated_request_tokens: Expected request size.
        responder_input_rate_per_mtok: Responder's input rate.
        reputation_score: Requestor's ARP score.
        base_multiplier: Responder's base deposit multiplier.
        interaction_id: Optional interaction ID to associate.

    Returns:
        A DepositRecord with COMMITTED status.
    """
    amount, tier = calculate_deposit(
        estimated_request_tokens,
        responder_input_rate_per_mtok,
        reputation_score,
        base_multiplier,
    )
    return DepositRecord(
        requestor_id=requestor_id,
        responder_id=responder_id,
        amount_usd=amount,
        status=DepositStatus.COMMITTED.value,
        interaction_id=interaction_id,
        multiplier=base_multiplier,
        reputation_tier=tier,
    )


def resolve_deposit(deposit: DepositRecord, is_spam: bool) -> DepositRecord:
    """Resolve a deposit after the interaction.

    Args:
        deposit: The deposit to resolve.
        is_spam: Whether the responder classified the request as spam.

    Returns:
        Updated DepositRecord with REFUNDED or FORFEITED status.
    """
    if is_spam:
        deposit.status = DepositStatus.FORFEITED.value
    else:
        deposit.status = DepositStatus.REFUNDED.value
    return deposit
