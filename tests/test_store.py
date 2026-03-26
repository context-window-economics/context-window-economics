"""Tests for store.py — JSONL persistence."""
import os
import tempfile

from context_window_economics.metering import Meter
from context_window_economics.schema import DepositRecord
from context_window_economics.store import CWEPStore


def _tmp_store():
    """Create a store in a temp directory."""
    d = tempfile.mkdtemp()
    return CWEPStore(store_dir=os.path.join(d, ".cwep"))


def test_append_and_read_cmr():
    store = _tmp_store()
    meter = Meter(agent_id="a", model="claude-sonnet-4-6", provider="anthropic")
    cmr = meter.record_interaction(
        responder_id="b", request_tokens=5000, response_tokens=2000,
    )
    store.append_cmr(cmr)
    assert store.cmr_count() == 1

    cmrs = store.read_cmrs()
    assert len(cmrs) == 1
    assert cmrs[0].interaction_id == cmr.interaction_id


def test_append_multiple_cmrs():
    store = _tmp_store()
    meter = Meter(agent_id="a", model="claude-sonnet-4-6", provider="anthropic")
    for _ in range(5):
        cmr = meter.record_interaction(
            responder_id="b", request_tokens=1000, response_tokens=500,
        )
        store.append_cmr(cmr)
    assert store.cmr_count() == 5

    recent = store.read_cmrs(limit=3)
    assert len(recent) == 3


def test_append_and_read_settlement():
    store = _tmp_store()
    store.append_settlement({"method": "shapley", "amount": 0.05})
    store.append_settlement({"method": "equal_split", "amount": 0.03})
    assert store.settlement_count() == 2

    records = store.read_settlements()
    assert len(records) == 2
    assert records[0]["method"] == "shapley"


def test_append_and_read_deposit():
    store = _tmp_store()
    dep = DepositRecord(requestor_id="a", responder_id="b", amount_usd=0.10)
    store.append_deposit(dep)
    assert store.deposit_count() == 1

    deps = store.read_deposits()
    assert len(deps) == 1
    assert deps[0].requestor_id == "a"


def test_statistics():
    store = _tmp_store()
    meter = Meter(agent_id="a", model="claude-sonnet-4-6", provider="anthropic")
    for _ in range(3):
        cmr = meter.record_interaction(
            responder_id="b", request_tokens=10000, response_tokens=3000,
        )
        store.append_cmr(cmr)

    stats = store.statistics()
    assert stats["cmr_count"] == 3
    assert abs(stats["total_cost_usd"] - 0.234 * 3) < 1e-4
    assert stats["total_tokens"] == 26000 * 3
    assert "a" in stats["agent_costs"]
    assert "b" in stats["agent_costs"]


def test_empty_store():
    store = _tmp_store()
    assert store.cmr_count() == 0
    assert store.settlement_count() == 0
    assert store.deposit_count() == 0
    assert store.read_cmrs() == []
    stats = store.statistics()
    assert stats["cmr_count"] == 0
    assert stats["total_cost_usd"] == 0.0
