"""CLI entry point for the Context Window Economics Protocol.

Commands:
    cwep meter     — Record and track interaction costs
    cwep allocate  — Compute fair cost split for an interaction
    cwep settle    — Generate settlement for recorded interactions
    cwep status    — Show cost summary from the store
"""
import argparse
import json
import sys
from typing import List, Optional

from .allocation import allocate
from .metering import Meter, estimate_interaction_cost
from .schema import (
    AllocationMethod,
    PROTOCOL_VERSION,
    QoSTier,
    SettlementTier,
)
from .store import CWEPStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cwep",
        description="Context Window Economics Protocol — bilateral cost allocation for agent interactions",
    )
    parser.add_argument("--version", action="version", version=f"cwep {PROTOCOL_VERSION}")
    parser.add_argument("--store", default=".cwep", help="Store directory (default: .cwep)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    sub = parser.add_subparsers(dest="command")

    # ---- meter ----
    meter_p = sub.add_parser("meter", help="Record interaction costs")
    meter_p.add_argument("--requestor", required=True, help="Requestor agent ID")
    meter_p.add_argument("--responder", required=True, help="Responder agent ID")
    meter_p.add_argument("--req-model", default="claude-sonnet-4-6", help="Requestor model")
    meter_p.add_argument("--resp-model", default="claude-sonnet-4-6", help="Responder model")
    meter_p.add_argument("--req-provider", default="anthropic", help="Requestor provider")
    meter_p.add_argument("--resp-provider", default="anthropic", help="Responder provider")
    meter_p.add_argument("--request-tokens", type=int, required=True, help="Request token count")
    meter_p.add_argument("--response-tokens", type=int, required=True, help="Response token count")
    meter_p.add_argument("--request-cached", type=int, default=0, help="Cached tokens in request")
    meter_p.add_argument("--response-cached", type=int, default=0, help="Cached tokens in response")

    # ---- allocate ----
    alloc_p = sub.add_parser("allocate", help="Compute cost allocation")
    alloc_p.add_argument("--requestor", required=True, help="Requestor agent ID")
    alloc_p.add_argument("--responder", required=True, help="Responder agent ID")
    alloc_p.add_argument("--req-model", default="claude-sonnet-4-6")
    alloc_p.add_argument("--resp-model", default="claude-sonnet-4-6")
    alloc_p.add_argument("--req-provider", default="anthropic")
    alloc_p.add_argument("--resp-provider", default="anthropic")
    alloc_p.add_argument("--request-tokens", type=int, required=True)
    alloc_p.add_argument("--response-tokens", type=int, required=True)
    alloc_p.add_argument(
        "--method", default="shapley",
        choices=[m.value for m in AllocationMethod],
        help="Allocation method",
    )
    alloc_p.add_argument("--alpha", type=float, default=0.5, help="Nash bargaining power (0-1)")
    alloc_p.add_argument("--value-a", type=float, default=1.0, help="Requestor value (Nash)")
    alloc_p.add_argument("--value-b", type=float, default=0.5, help="Responder value (Nash)")

    # ---- settle ----
    settle_p = sub.add_parser("settle", help="Generate settlement from store")
    settle_p.add_argument(
        "--method", default="shapley",
        choices=[m.value for m in AllocationMethod],
    )
    settle_p.add_argument("--limit", type=int, default=0, help="Max CMRs to process (0=all)")

    # ---- status ----
    sub.add_parser("status", help="Show cost summary")

    # ---- estimate ----
    est_p = sub.add_parser("estimate", help="Quick cost estimate (no store write)")
    est_p.add_argument("--request-tokens", type=int, required=True)
    est_p.add_argument("--response-tokens", type=int, required=True)
    est_p.add_argument("--req-model", default="claude-sonnet-4-6")
    est_p.add_argument("--resp-model", default="claude-sonnet-4-6")
    est_p.add_argument("--req-provider", default="anthropic")
    est_p.add_argument("--resp-provider", default="anthropic")

    return parser


def _cmd_meter(args: argparse.Namespace) -> dict:
    meter = Meter(
        agent_id=args.requestor,
        model=args.req_model,
        provider=args.req_provider,
    )
    cmr = meter.record_interaction(
        responder_id=args.responder,
        responder_model=args.resp_model,
        responder_provider=args.resp_provider,
        request_tokens=args.request_tokens,
        response_tokens=args.response_tokens,
        request_cached_tokens=args.request_cached,
        response_cached_tokens=args.response_cached,
    )
    store = CWEPStore(args.store)
    store.append_cmr(cmr)
    return cmr.to_dict()


def _cmd_allocate(args: argparse.Namespace) -> dict:
    meter = Meter(
        agent_id=args.requestor,
        model=args.req_model,
        provider=args.req_provider,
    )
    cmr = meter.record_interaction(
        responder_id=args.responder,
        responder_model=args.resp_model,
        responder_provider=args.resp_provider,
        request_tokens=args.request_tokens,
        response_tokens=args.response_tokens,
    )
    proposal = allocate(
        cmr,
        method=args.method,
        alpha=args.alpha,
        value_a=args.value_a,
        value_b=args.value_b,
    )
    return {
        "interaction": cmr.to_dict(),
        "allocation": proposal.to_dict(),
    }


def _cmd_settle(args: argparse.Namespace) -> dict:
    store = CWEPStore(args.store)
    cmrs = store.read_cmrs(limit=args.limit)
    results = []
    for cmr in cmrs:
        proposal = allocate(cmr, method=args.method)
        results.append({
            "interaction_id": cmr.interaction_id,
            "total_cost": cmr.totals.total_cost_usd,
            "allocation": proposal.to_dict(),
        })
        store.append_settlement({
            "interaction_id": cmr.interaction_id,
            "method": args.method,
            **proposal.to_dict(),
        })
    return {"settlements": results, "count": len(results)}


def _cmd_status(args: argparse.Namespace) -> dict:
    store = CWEPStore(args.store)
    return store.statistics()


def _cmd_estimate(args: argparse.Namespace) -> dict:
    return estimate_interaction_cost(
        request_tokens=args.request_tokens,
        response_tokens=args.response_tokens,
        requestor_model=args.req_model,
        requestor_provider=args.req_provider,
        responder_model=args.resp_model,
        responder_provider=args.resp_provider,
    )


def _format_output(data: dict, as_json: bool) -> str:
    if as_json:
        return json.dumps(data, indent=2, default=str)

    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k2, v2 in value.items():
                if isinstance(v2, float):
                    lines.append(f"  {k2}: ${v2:.6f}")
                else:
                    lines.append(f"  {k2}: {v2}")
        elif isinstance(value, float):
            lines.append(f"{key}: ${value:.6f}")
        elif isinstance(value, list):
            lines.append(f"{key}: ({len(value)} items)")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "meter": _cmd_meter,
        "allocate": _cmd_allocate,
        "settle": _cmd_settle,
        "status": _cmd_status,
        "estimate": _cmd_estimate,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    result = handler(args)
    print(_format_output(result, args.json))


if __name__ == "__main__":
    main()
