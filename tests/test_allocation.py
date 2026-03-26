"""Tests for allocation.py — cost allocation methods."""
from context_window_economics.allocation import (
    allocate,
    allocate_equal_split,
    allocate_nash,
    allocate_proportional,
    allocate_requestor_pays,
    allocate_responder_pays,
    allocate_shapley,
)
from context_window_economics.metering import Meter


def _make_cmr():
    """Create the whitepaper Section 4.1 example CMR (Sonnet 4.6)."""
    meter = Meter(agent_id="agent-a", model="claude-sonnet-4-6", provider="anthropic")
    return meter.record_interaction(
        responder_id="agent-b",
        responder_model="claude-sonnet-4-6",
        responder_provider="anthropic",
        request_tokens=10000,
        response_tokens=3000,
    )


def test_requestor_pays():
    cmr = _make_cmr()
    p = allocate_requestor_pays(cmr)
    assert abs(p.requestor_pays_usd - 0.234) < 1e-6
    assert abs(p.responder_pays_usd) < 1e-6
    assert p.transfer_direction == "requestor_to_responder"


def test_responder_pays():
    cmr = _make_cmr()
    p = allocate_responder_pays(cmr)
    assert abs(p.responder_pays_usd - 0.234) < 1e-6
    assert abs(p.requestor_pays_usd) < 1e-6
    assert p.transfer_direction == "responder_to_requestor"


def test_equal_split():
    cmr = _make_cmr()
    p = allocate_equal_split(cmr)
    assert abs(p.requestor_pays_usd - 0.117) < 1e-6
    assert abs(p.responder_pays_usd - 0.117) < 1e-6


def test_proportional():
    cmr = _make_cmr()
    p = allocate_proportional(cmr)
    # Requestor tokens: RO(10000) + SI(3000) = 13000 out of 26000 = 50%
    assert abs(p.requestor_pays_usd - 0.117) < 1e-6
    assert abs(p.responder_pays_usd - 0.117) < 1e-6


def test_shapley():
    """Test Shapley against whitepaper Section 8.2 calculation."""
    cmr = _make_cmr()
    p = allocate_shapley(cmr)
    # shapley_a = RO + (RI + SO + SI) / 2 = 0.150 + (0.030 + 0.045 + 0.009) / 2 = 0.150 + 0.042 = 0.192
    assert abs(p.requestor_pays_usd - 0.192) < 1e-6
    # shapley_b = (RI + SO + SI) / 2 = 0.042
    assert abs(p.responder_pays_usd - 0.042) < 1e-6
    # Budget balanced
    assert abs(p.requestor_pays_usd + p.responder_pays_usd - 0.234) < 1e-6


def test_shapley_with_standing_costs():
    """Test Shapley with standalone_cost_b > 0 from whitepaper."""
    cmr = _make_cmr()
    p = allocate_shapley(cmr, standalone_cost_b=0.02)
    # shapley_a = (0.234 + 0.150 - 0.02) / 2 = 0.182
    assert abs(p.requestor_pays_usd - 0.182) < 1e-6
    # shapley_b = (0.234 + 0.02 - 0.150) / 2 = 0.052
    assert abs(p.responder_pays_usd - 0.052) < 1e-6


def test_nash_bargaining():
    cmr = _make_cmr()
    p = allocate_nash(cmr, value_a=1.0, value_b=0.5, alpha=0.6)
    # Both payments should be non-negative and sum to total
    assert p.requestor_pays_usd >= 0
    assert p.responder_pays_usd >= 0
    assert abs(p.requestor_pays_usd + p.responder_pays_usd - 0.234) < 1e-6


def test_nash_no_surplus_falls_back():
    """When surplus <= 0, Nash falls back to proportional."""
    cmr = _make_cmr()
    p = allocate_nash(cmr, value_a=0.01, value_b=0.01, alpha=0.5)
    assert p.method == "proportional"


def test_allocate_dispatcher():
    cmr = _make_cmr()
    p = allocate(cmr, method="shapley")
    assert p.method == "shapley"
    p2 = allocate(cmr, method="equal_split")
    assert p2.method == "equal_split"


def test_budget_balance_all_methods():
    """All allocation methods must be budget-balanced."""
    cmr = _make_cmr()
    total = cmr.totals.total_cost_usd

    for method in ["requestor_pays", "responder_pays", "equal_split", "proportional", "shapley"]:
        p = allocate(cmr, method=method)
        assert abs(p.requestor_pays_usd + p.responder_pays_usd - total) < 1e-6, (
            f"{method} not budget-balanced"
        )
