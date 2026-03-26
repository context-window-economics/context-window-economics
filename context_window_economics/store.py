"""Append-only JSONL store for metering records and settlements.

Provides persistent storage for CMRs, settlement receipts, and deposit records.
All writes are append-only for auditability.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

from .schema import CostMeteringRecord, DepositRecord, SettlementProposal

T = TypeVar("T")

DEFAULT_STORE_DIR = ".cwep"
CMR_FILE = "metering.jsonl"
SETTLEMENT_FILE = "settlements.jsonl"
DEPOSIT_FILE = "deposits.jsonl"


class CWEPStore:
    """Append-only JSONL store for CWEP records.

    Files are stored in a directory (default: .cwep/ in working dir).
    Each record type gets its own JSONL file.
    """

    def __init__(self, store_dir: str = DEFAULT_STORE_DIR):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._cmr_path = self.store_dir / CMR_FILE
        self._settlement_path = self.store_dir / SETTLEMENT_FILE
        self._deposit_path = self.store_dir / DEPOSIT_FILE

    # ----- CMR operations -----

    def append_cmr(self, cmr: CostMeteringRecord) -> None:
        """Append a CMR to the metering log."""
        self._append(self._cmr_path, cmr.to_dict())

    def read_cmrs(self, limit: int = 0) -> List[CostMeteringRecord]:
        """Read CMRs from the store.

        Args:
            limit: Maximum number to return (0 = all, most recent first).
        """
        records = self._read_all(self._cmr_path)
        if limit > 0:
            records = records[-limit:]
        return [CostMeteringRecord.from_dict(r) for r in records]

    def cmr_count(self) -> int:
        """Count CMRs in the store."""
        return self._count_lines(self._cmr_path)

    # ----- Settlement operations -----

    def append_settlement(self, data: Dict[str, Any]) -> None:
        """Append a settlement record."""
        self._append(self._settlement_path, data)

    def read_settlements(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Read settlement records."""
        records = self._read_all(self._settlement_path)
        if limit > 0:
            records = records[-limit:]
        return records

    def settlement_count(self) -> int:
        return self._count_lines(self._settlement_path)

    # ----- Deposit operations -----

    def append_deposit(self, deposit: DepositRecord) -> None:
        """Append a deposit record."""
        self._append(self._deposit_path, deposit.to_dict())

    def read_deposits(self, limit: int = 0) -> List[DepositRecord]:
        """Read deposit records."""
        records = self._read_all(self._deposit_path)
        if limit > 0:
            records = records[-limit:]
        return [DepositRecord.from_dict(r) for r in records]

    def deposit_count(self) -> int:
        return self._count_lines(self._deposit_path)

    # ----- Aggregate statistics -----

    def statistics(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all stored records."""
        cmrs = self.read_cmrs()
        total_cost = sum(c.totals.total_cost_usd for c in cmrs)
        total_tokens = sum(c.totals.total_tokens for c in cmrs)

        # Per-agent cost breakdown
        agent_costs: Dict[str, float] = {}
        for c in cmrs:
            if c.requestor:
                aid = c.requestor.agent_id
                agent_costs[aid] = agent_costs.get(aid, 0.0) + c.totals.requestor_incurred_usd
            if c.responder:
                aid = c.responder.agent_id
                agent_costs[aid] = agent_costs.get(aid, 0.0) + c.totals.responder_incurred_usd

        return {
            "cmr_count": len(cmrs),
            "settlement_count": self.settlement_count(),
            "deposit_count": self.deposit_count(),
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "agent_costs": agent_costs,
            "store_dir": str(self.store_dir),
        }

    # ----- Internal -----

    def _append(self, path: Path, data: Dict[str, Any]) -> None:
        """Append a JSON record as a single line."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, default=str) + "\n")

    def _read_all(self, path: Path) -> List[Dict[str, Any]]:
        """Read all JSONL records from a file."""
        if not path.exists():
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _count_lines(self, path: Path) -> int:
        """Count non-empty lines in a JSONL file."""
        if not path.exists():
            return 0
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
