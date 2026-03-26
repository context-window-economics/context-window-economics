"""Tests for metering.py — token metering and CMR generation."""
from context_window_economics.metering import (
    Meter,
    compute_flow_cost,
    estimate_interaction_cost,
)
from context_window_economics.schema import CostFlow


def test_meter_record_interaction():
    meter = Meter(agent_id="agent-a", model="claude-sonnet-4-6", provider="anthropic")
    cmr = meter.record_interaction(
        responder_id="agent-b",
        responder_model="claude-sonnet-4-6",
        responder_provider="anthropic",
        request_tokens=10000,
        response_tokens=3000,
    )
    assert cmr.requestor.agent_id == "agent-a"
    assert cmr.responder.agent_id == "agent-b"
    assert cmr.totals.total_tokens == 26000
    assert abs(cmr.totals.total_cost_usd - 0.234) < 1e-6


def test_meter_with_caching():
    meter = Meter(agent_id="agent-a", model="claude-sonnet-4-6", provider="anthropic")
    cmr = meter.record_interaction(
        responder_id="agent-b",
        request_tokens=10000,
        request_cached_tokens=3000,
        response_tokens=3000,
    )
    # RI should be cheaper due to caching
    ri_cost = cmr.flows[CostFlow.REQUEST_INPUT.value].cost_usd
    # 7000 * 3.0/1M + 3000 * 0.3/1M = 0.021 + 0.0009 = 0.0219
    assert abs(ri_cost - 0.0219) < 1e-6


def test_meter_record_flows():
    meter = Meter(agent_id="a", model="claude-sonnet-4-6", provider="anthropic")
    cmr = meter.record_flows(
        responder_id="b",
        ro_tokens=5000,
        ri_tokens=5500,  # With protocol overhead
        so_tokens=2000,
        si_tokens=2000,
    )
    assert cmr.flows[CostFlow.REQUEST_OUTPUT.value].tokens == 5000
    assert cmr.flows[CostFlow.REQUEST_INPUT.value].tokens == 5500
    assert cmr.totals.total_tokens == 14500


def test_meter_opus_pricing():
    """Test with Opus 4.6 pricing from whitepaper Section 4.1."""
    meter = Meter(agent_id="a", model="claude-opus-4-6", provider="anthropic")
    cmr = meter.record_interaction(
        responder_id="b",
        responder_model="claude-opus-4-6",
        responder_provider="anthropic",
        request_tokens=10000,
        response_tokens=3000,
    )
    # RO: 10000 * 25/1M = $0.250
    assert abs(cmr.flows[CostFlow.REQUEST_OUTPUT.value].cost_usd - 0.250) < 1e-6
    # RI: 10000 * 5/1M = $0.050
    assert abs(cmr.flows[CostFlow.REQUEST_INPUT.value].cost_usd - 0.050) < 1e-6
    # SO: 3000 * 25/1M = $0.075
    assert abs(cmr.flows[CostFlow.RESPONSE_OUTPUT.value].cost_usd - 0.075) < 1e-6
    # SI: 3000 * 5/1M = $0.015
    assert abs(cmr.flows[CostFlow.RESPONSE_INPUT.value].cost_usd - 0.015) < 1e-6
    # Total: $0.390
    assert abs(cmr.totals.total_cost_usd - 0.390) < 1e-6


def test_compute_flow_cost():
    cost = compute_flow_cost(tokens=10000, rate_per_mtok=3.0)
    assert abs(cost - 0.03) < 1e-9

    cost_cached = compute_flow_cost(
        tokens=10000, rate_per_mtok=3.0,
        cached_tokens=5000, cache_rate_per_mtok=0.3,
    )
    # 5000 * 3.0/1M + 5000 * 0.3/1M = 0.015 + 0.0015 = 0.0165
    assert abs(cost_cached - 0.0165) < 1e-9


def test_estimate_interaction_cost():
    est = estimate_interaction_cost(
        request_tokens=10000,
        response_tokens=3000,
        requestor_model="claude-sonnet-4-6",
        responder_model="claude-sonnet-4-6",
    )
    assert abs(est["total"] - 0.234) < 1e-6
    assert abs(est["requestor_incurred"] - 0.159) < 1e-6
    assert abs(est["responder_incurred"] - 0.075) < 1e-6
