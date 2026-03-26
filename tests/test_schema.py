"""Tests for schema.py — data structures and serialization."""
import json

from context_window_economics.schema import (
    AgentInfo,
    AgentPricing,
    CostFlow,
    CostMeteringRecord,
    ContextState,
    DepositRecord,
    InteractionTotals,
    QoSConfig,
    SettlementProposal,
    TokenFlow,
    BackPressureSignal,
    ContextReservation,
    PROTOCOL_VERSION,
)


def test_agent_pricing_from_provider():
    p = AgentPricing.from_provider("anthropic", "claude-sonnet-4-6")
    assert p.input_rate_per_mtok == 3.00
    assert p.output_rate_per_mtok == 15.00
    assert p.cache_hit_rate_per_mtok == 0.30


def test_agent_pricing_cost_calculations():
    p = AgentPricing(input_rate_per_mtok=3.0, output_rate_per_mtok=15.0, cache_hit_rate_per_mtok=0.3)
    # 10000 tokens at $3/MTok = $0.03
    assert abs(p.input_cost(10000) - 0.03) < 1e-9
    # 10000 tokens, 3000 cached: 7000 * 3.0/1M + 3000 * 0.3/1M = 0.021 + 0.0009 = 0.0219
    assert abs(p.input_cost(10000, 3000) - 0.0219) < 1e-9
    # 3000 output tokens at $15/MTok = $0.045
    assert abs(p.output_cost(3000) - 0.045) < 1e-9


def test_agent_pricing_roundtrip():
    p = AgentPricing(input_rate_per_mtok=5.0, output_rate_per_mtok=25.0, cache_hit_rate_per_mtok=0.5)
    d = p.to_dict()
    p2 = AgentPricing.from_dict(d)
    assert p2.input_rate_per_mtok == 5.0
    assert p2.output_rate_per_mtok == 25.0


def test_cmr_compute_costs():
    """Test the whitepaper Section 4.1 code review example (Sonnet 4.6)."""
    cmr = CostMeteringRecord(
        requestor=AgentInfo(
            agent_id="agent-a", model="claude-sonnet-4-6", provider="anthropic",
            pricing=AgentPricing.from_provider("anthropic", "claude-sonnet-4-6"),
        ),
        responder=AgentInfo(
            agent_id="agent-b", model="claude-sonnet-4-6", provider="anthropic",
            pricing=AgentPricing.from_provider("anthropic", "claude-sonnet-4-6"),
        ),
        flows={
            CostFlow.REQUEST_OUTPUT.value: TokenFlow(tokens=10000),
            CostFlow.REQUEST_INPUT.value: TokenFlow(tokens=10000),
            CostFlow.RESPONSE_OUTPUT.value: TokenFlow(tokens=3000),
            CostFlow.RESPONSE_INPUT.value: TokenFlow(tokens=3000),
        },
    )
    cmr.compute_costs()

    # RO: 10000 * 15/1M = $0.150
    assert abs(cmr.flows[CostFlow.REQUEST_OUTPUT.value].cost_usd - 0.150) < 1e-6
    # RI: 10000 * 3/1M = $0.030
    assert abs(cmr.flows[CostFlow.REQUEST_INPUT.value].cost_usd - 0.030) < 1e-6
    # SO: 3000 * 15/1M = $0.045
    assert abs(cmr.flows[CostFlow.RESPONSE_OUTPUT.value].cost_usd - 0.045) < 1e-6
    # SI: 3000 * 3/1M = $0.009
    assert abs(cmr.flows[CostFlow.RESPONSE_INPUT.value].cost_usd - 0.009) < 1e-6
    # Total: $0.234
    assert abs(cmr.totals.total_cost_usd - 0.234) < 1e-6
    assert cmr.totals.total_tokens == 26000


def test_cmr_json_roundtrip():
    cmr = CostMeteringRecord(
        requestor=AgentInfo(
            agent_id="a", model="claude-sonnet-4-6", provider="anthropic",
            pricing=AgentPricing(3.0, 15.0, 0.3),
        ),
        responder=AgentInfo(
            agent_id="b", model="claude-sonnet-4-6", provider="anthropic",
            pricing=AgentPricing(3.0, 15.0, 0.3),
        ),
    )
    cmr.compute_costs()
    j = cmr.to_json()
    cmr2 = CostMeteringRecord.from_json(j)
    assert cmr2.interaction_id == cmr.interaction_id
    assert cmr2.cwep_version == PROTOCOL_VERSION


def test_deposit_record_roundtrip():
    d = DepositRecord(requestor_id="a", responder_id="b", amount_usd=0.05)
    data = d.to_dict()
    d2 = DepositRecord.from_dict(data)
    assert d2.requestor_id == "a"
    assert d2.amount_usd == 0.05


def test_qos_config_roundtrip():
    q = QoSConfig(tier="priority", input_tokens_per_minute=2000000)
    data = q.to_dict()
    q2 = QoSConfig.from_dict(data)
    assert q2.tier == "priority"
    assert q2.input_tokens_per_minute == 2000000


def test_settlement_proposal_roundtrip():
    sp = SettlementProposal(
        method="shapley", requestor_pays_usd=0.192,
        responder_pays_usd=0.042, net_transfer_usd=0.033,
        transfer_direction="requestor_to_responder",
    )
    data = sp.to_dict()
    sp2 = SettlementProposal.from_dict(data)
    assert abs(sp2.requestor_pays_usd - 0.192) < 1e-6


def test_back_pressure_signal():
    bp = BackPressureSignal(cwep_status="congested", current_utilization=0.87)
    data = bp.to_dict()
    bp2 = BackPressureSignal.from_dict(data)
    assert bp2.cwep_status == "congested"
    assert bp2.current_utilization == 0.87


def test_context_reservation_roundtrip():
    cr = ContextReservation(
        requestor_id="a", responder_id="b",
        capacity_tokens=100000, price_usd=0.50,
    )
    data = cr.to_dict()
    cr2 = ContextReservation.from_dict(data)
    assert cr2.capacity_tokens == 100000
    assert cr2.price_usd == 0.50
