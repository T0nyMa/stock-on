#!/usr/bin/env python3
"""Validate and persist deep-research snapshots in the project database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


KINDS = {"research_evidence", "research_summary"}
QUALITIES = {"primary", "authoritative", "secondary", "weak"}
STATUSES = {"verified", "conflicting", "unverified"}


def _required(payload: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if payload.get(field) in (None, "", []))
    if missing:
        raise ValueError(f"{label} missing required fields: {', '.join(missing)}")


def validate_payload(kind: str, payload: dict[str, Any]) -> None:
    if kind not in KINDS:
        raise ValueError(f"unsupported snapshot kind: {kind}")
    _required(payload, {"schema_version", "as_of"}, kind)
    if payload["schema_version"] != 1:
        raise ValueError("schema_version must be 1")

    if kind == "research_evidence":
        _required(payload, {"items"}, kind)
        if not isinstance(payload["items"], list):
            raise ValueError("items must be a list")
        fields = {"claim", "value", "period", "source_type", "source", "published_at", "url", "quality", "status"}
        for index, item in enumerate(payload["items"]):
            if not isinstance(item, dict):
                raise ValueError(f"evidence item {index} must be an object")
            _required(item, fields, f"evidence item {index}")
            if item["quality"] not in QUALITIES:
                raise ValueError(f"invalid evidence quality: {item['quality']}")
            if item["status"] not in STATUSES:
                raise ValueError(f"invalid evidence status: {item['status']}")
    else:
        _required(payload, {"company_type", "thesis", "falsification", "confidence", "source_report"}, kind)
        company_type = payload["company_type"]
        if not isinstance(company_type, dict) or not company_type.get("primary"):
            raise ValueError("company_type.primary is required")
        if payload["confidence"] not in {"high", "medium", "low"}:
            raise ValueError("confidence must be high, medium, or low")
        if not isinstance(payload["thesis"], list) or not isinstance(payload["falsification"], list):
            raise ValueError("thesis and falsification must be lists")


def save_payload(store: Any, code: str, name: str, market: str, kind: str, payload: dict[str, Any]) -> None:
    validate_payload(kind, payload)
    store.save_snapshot(code, name, market, kind, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/stock_analysis.db")
    parser.add_argument("--code", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--kind", required=True, choices=sorted(KINDS))
    parser.add_argument("--input", required=True, help="JSON input file")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root))
    from src.storage import MarketDataStore

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    save_payload(MarketDataStore(args.db), args.code, args.name, args.market, args.kind, payload)
    print(json.dumps({"code": args.code, "kind": args.kind, "status": "saved"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
