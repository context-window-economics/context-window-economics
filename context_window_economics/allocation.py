"""Cost allocation engine for bilateral agent interactions.

Implements three allocation families:
  1. Rule-based: requestor-pays, responder-pays, equal split, proportional
  2. Shapley value: fair division based on marginal contribution
  3. Nash bargaining: bilateral negotiation with bargaining power

All methods take a CostMeteringRecord and return a SettlementProposal.
"""
from typing import Optional

from .schema import (
    AllocationMethod,
    CostFlow,
    CostMeteringRecord,
    SettlementProposal,
)


# ---------------------------------------------------------------------------
# Rule-based allocation (Tier 2)
# ---------------------------------------------------------------------------

def allocate_requestor_pays(cmr: CostMeteringRecord) -> SettlementProposal:
    """Requestor pays 100% of total interaction cost."""
    total = cmr.totals.total_cost_usd
    responder_incurred = cmr.totals.responder_incurred_usd
    return SettlementProposal(
        method=AllocationMethod.REQUESTOR_PAYS.value,
        requestor_pays_usd=total,
        responder_pays_usd=0.0,
        net_transfer_usd=responder_incurred,
        transfer_direction="requestor_to_responder",
    )


def allocate_responder_pays(cmr: CostMeteringRecord) -> SettlementProposal:
    """Responder pays 100% of total interaction cost."""
    total = cmr.totals.total_cost_usd
    requestor_incurred = cmr.totals.requestor_incurred_usd
    return SettlementProposal(
        method=AllocationMethod.RESPONDER_PAYS.value,
        requestor_pays_usd=0.0,
        responder_pays_usd=total,
        net_transfer_usd=requestor_incurred,
        transfer_direction="responder_to_requestor",
    )


def allocate_equal_split(cmr: CostMeteringRecord) -> SettlementProposal:
    """Each agent pays 50% of total interaction cost."""
    total = cmr.totals.total_cost_usd
    half = total / 2.0
    req_incurred = cmr.totals.requestor_incurred_usd
    resp_incurred = cmr.totals.responder_incurred_usd

    # Net transfer: whoever incurred more than their 50% share gets reimbursed
    if req_incurred > half:
        net = req_incurred - half
        direction = "responder_to_requestor"
    else:
        net = resp_incurred - half
        direction = "requestor_to_responder"

    return SettlementProposal(
        method=AllocationMethod.EQUAL_SPLIT.value,
        requestor_pays_usd=half,
        responder_pays_usd=half,
        net_transfer_usd=abs(net),
        transfer_direction=direction,
    )


def allocate_proportional(cmr: CostMeteringRecord) -> SettlementProposal:
    """Each agent pays proportional to tokens they consumed (generated + processed)."""
    ro = cmr.flows[CostFlow.REQUEST_OUTPUT.value].tokens
    ri = cmr.flows[CostFlow.REQUEST_INPUT.value].tokens
    so = cmr.flows[CostFlow.RESPONSE_OUTPUT.value].tokens
    si = cmr.flows[CostFlow.RESPONSE_INPUT.value].tokens

    total_tokens = ro + ri + so + si
    if total_tokens == 0:
        return SettlementProposal(
            method=AllocationMethod.PROPORTIONAL.value,
            requestor_pays_usd=0.0,
            responder_pays_usd=0.0,
            net_transfer_usd=0.0,
            transfer_direction="",
        )

    # Requestor's token share: generated request + processed response
    req_tokens = ro + si
    req_share = req_tokens / total_tokens

    total = cmr.totals.total_cost_usd
    req_pays = total * req_share
    resp_pays = total * (1.0 - req_share)

    req_incurred = cmr.totals.requestor_incurred_usd
    net = req_pays - req_incurred
    if net >= 0:
        direction = "requestor_to_responder"
    else:
        direction = "responder_to_requestor"
        net = -net

    return SettlementProposal(
        method=AllocationMethod.PROPORTIONAL.value,
        requestor_pays_usd=req_pays,
        responder_pays_usd=resp_pays,
        net_transfer_usd=net,
        transfer_direction=direction,
    )


# ---------------------------------------------------------------------------
# Shapley value allocation (Tier 3)
# ---------------------------------------------------------------------------

def allocate_shapley(
    cmr: CostMeteringRecord,
    standalone_cost_b: float = 0.0,
) -> SettlementProposal:
    """Shapley value cost allocation for a two-agent interaction.

    From the whitepaper (Section 8.2):
        standalone_cost(A) = RO  (A generates request, no response)
        standalone_cost(B) = 0   (B does nothing without a request)
        joint_cost(A,B) = RO + RI + SO + SI

        shapley_payment(A) = RO + (RI + SO + SI) / 2
        shapley_payment(B) = (RI + SO + SI) / 2

    When standalone_cost_b > 0 (responder standing costs):
        shapley_payment(A) = [joint + standalone_a - standalone_b] / 2
        shapley_payment(B) = [joint + standalone_b - standalone_a] / 2

    Args:
        cmr: The cost metering record.
        standalone_cost_b: Responder's per-interaction infrastructure cost.

    Returns:
        SettlementProposal with Shapley allocation.
    """
    ro = cmr.flows[CostFlow.REQUEST_OUTPUT.value].cost_usd
    ri = cmr.flows[CostFlow.REQUEST_INPUT.value].cost_usd
    so = cmr.flows[CostFlow.RESPONSE_OUTPUT.value].cost_usd
    si = cmr.flows[CostFlow.RESPONSE_INPUT.value].cost_usd

    joint = ro + ri + so + si
    standalone_a = ro  # Requestor's standalone cost

    shapley_a = (joint + standalone_a - standalone_cost_b) / 2.0
    shapley_b = (joint + standalone_cost_b - standalone_a) / 2.0

    # Clamp to non-negative
    shapley_a = max(0.0, shapley_a)
    shapley_b = max(0.0, shapley_b)

    # Net transfer: compare what each should pay vs what they already incurred
    req_incurred = cmr.totals.requestor_incurred_usd
    net = shapley_a - req_incurred
    if net >= 0:
        direction = "requestor_to_responder"
    else:
        direction = "responder_to_requestor"
        net = -net

    return SettlementProposal(
        method=AllocationMethod.SHAPLEY.value,
        requestor_pays_usd=shapley_a,
        responder_pays_usd=shapley_b,
        net_transfer_usd=net,
        transfer_direction=direction,
        parameters={"standalone_cost_b": standalone_cost_b},
    )


# ---------------------------------------------------------------------------
# Nash bargaining allocation (Tier 3)
# ---------------------------------------------------------------------------

def allocate_nash(
    cmr: CostMeteringRecord,
    value_a: float,
    value_b: float,
    alpha: float = 0.5,
    disagreement_a: float = 0.0,
    disagreement_b: float = 0.0,
) -> SettlementProposal:
    """Nash bargaining cost allocation for bilateral negotiation.

    From the whitepaper (Section 8.3):
        Nash solution maximizes:
            [utility(A) - disagreement(A)]^alpha * [utility(B) - disagreement(B)]^(1-alpha)

    The bargaining power parameter alpha can be derived from ARP scores,
    context utilization, or interaction history.

    Args:
        cmr: The cost metering record.
        value_a: Value the requestor receives from the interaction (USD).
        value_b: Value the responder receives from the interaction (USD).
        alpha: Requestor's bargaining power (0.0 to 1.0).
        disagreement_a: Requestor's value if negotiation fails.
        disagreement_b: Responder's value if negotiation fails.

    Returns:
        SettlementProposal with Nash bargaining allocation.
    """
    total_cost = cmr.totals.total_cost_usd

    # Surplus = total value - total cost - disagreement values
    surplus = (value_a + value_b) - total_cost - (disagreement_a + disagreement_b)

    if surplus <= 0:
        # No beneficial trade — fall back to proportional
        return allocate_proportional(cmr)

    # Nash solution: each agent's payment = their share of surplus deducted from value
    # Agent A pays: value_a - disagreement_a - alpha * surplus
    payment_a = value_a - disagreement_a - alpha * surplus
    payment_b = value_b - disagreement_b - (1.0 - alpha) * surplus

    # Clamp to [0, total_cost] and ensure budget balance
    payment_a = max(0.0, min(total_cost, payment_a))
    payment_b = total_cost - payment_a

    req_incurred = cmr.totals.requestor_incurred_usd
    net = payment_a - req_incurred
    if net >= 0:
        direction = "requestor_to_responder"
    else:
        direction = "responder_to_requestor"
        net = -net

    return SettlementProposal(
        method=AllocationMethod.NASH_BARGAINING.value,
        requestor_pays_usd=payment_a,
        responder_pays_usd=payment_b,
        net_transfer_usd=net,
        transfer_direction=direction,
        parameters={
            "alpha": alpha,
            "value_a": value_a,
            "value_b": value_b,
            "disagreement_a": disagreement_a,
            "disagreement_b": disagreement_b,
            "surplus": surplus,
        },
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def allocate(
    cmr: CostMeteringRecord,
    method: str = AllocationMethod.SHAPLEY.value,
    **kwargs,
) -> SettlementProposal:
    """Dispatch to the appropriate allocation method.

    Args:
        cmr: The cost metering record.
        method: One of AllocationMethod values.
        **kwargs: Method-specific parameters (e.g., alpha, value_a, value_b).

    Returns:
        SettlementProposal.
    """
    dispatch = {
        AllocationMethod.REQUESTOR_PAYS.value: lambda: allocate_requestor_pays(cmr),
        AllocationMethod.RESPONDER_PAYS.value: lambda: allocate_responder_pays(cmr),
        AllocationMethod.EQUAL_SPLIT.value: lambda: allocate_equal_split(cmr),
        AllocationMethod.PROPORTIONAL.value: lambda: allocate_proportional(cmr),
        AllocationMethod.SHAPLEY.value: lambda: allocate_shapley(
            cmr, standalone_cost_b=kwargs.get("standalone_cost_b", 0.0)
        ),
        AllocationMethod.NASH_BARGAINING.value: lambda: allocate_nash(
            cmr,
            value_a=kwargs.get("value_a", 0.0),
            value_b=kwargs.get("value_b", 0.0),
            alpha=kwargs.get("alpha", 0.5),
            disagreement_a=kwargs.get("disagreement_a", 0.0),
            disagreement_b=kwargs.get("disagreement_b", 0.0),
        ),
        AllocationMethod.BENEFICIARY_PAYS.value: lambda: allocate_proportional(cmr),
    }
    fn = dispatch.get(method)
    if fn is None:
        raise ValueError(f"Unknown allocation method: {method}")
    return fn()
