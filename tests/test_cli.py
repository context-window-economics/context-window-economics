"""Tests for cli.py — CLI commands."""
import json
import os
import tempfile

from context_window_economics.cli import main


def _run_cli(args, store_dir=None):
    """Run CLI with args and capture output."""
    if store_dir is None:
        store_dir = os.path.join(tempfile.mkdtemp(), ".cwep")
    full_args = ["--store", store_dir, "--json"] + args
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = buf = io.StringIO()
    try:
        main(full_args)
    finally:
        sys.stdout = old_stdout
    return json.loads(buf.getvalue())


def test_cli_estimate():
    result = _run_cli([
        "estimate",
        "--request-tokens", "10000",
        "--response-tokens", "3000",
    ])
    assert abs(result["total"] - 0.234) < 1e-6


def test_cli_estimate_opus():
    result = _run_cli([
        "estimate",
        "--request-tokens", "10000",
        "--response-tokens", "3000",
        "--req-model", "claude-opus-4-6",
        "--resp-model", "claude-opus-4-6",
    ])
    assert abs(result["total"] - 0.390) < 1e-6


def test_cli_meter():
    store_dir = os.path.join(tempfile.mkdtemp(), ".cwep")
    result = _run_cli([
        "meter",
        "--requestor", "agent-a",
        "--responder", "agent-b",
        "--request-tokens", "5000",
        "--response-tokens", "2000",
    ], store_dir=store_dir)
    assert "interaction_id" in result
    assert result["totals"]["total_tokens"] == 14000


def test_cli_allocate():
    result = _run_cli([
        "allocate",
        "--requestor", "agent-a",
        "--responder", "agent-b",
        "--request-tokens", "10000",
        "--response-tokens", "3000",
        "--method", "shapley",
    ])
    assert "allocation" in result
    assert abs(result["allocation"]["requestor_pays_usd"] - 0.192) < 1e-6


def test_cli_settle():
    store_dir = os.path.join(tempfile.mkdtemp(), ".cwep")
    # First meter some interactions
    for _ in range(3):
        _run_cli([
            "meter",
            "--requestor", "a",
            "--responder", "b",
            "--request-tokens", "10000",
            "--response-tokens", "3000",
        ], store_dir=store_dir)

    result = _run_cli(["settle", "--method", "shapley"], store_dir=store_dir)
    assert result["count"] == 3
    assert len(result["settlements"]) == 3


def test_cli_status():
    store_dir = os.path.join(tempfile.mkdtemp(), ".cwep")
    _run_cli([
        "meter", "--requestor", "a", "--responder", "b",
        "--request-tokens", "5000", "--response-tokens", "2000",
    ], store_dir=store_dir)

    result = _run_cli(["status"], store_dir=store_dir)
    assert result["cmr_count"] == 1
    assert result["total_tokens"] == 14000
