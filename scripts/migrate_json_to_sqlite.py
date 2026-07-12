#!/usr/bin/env python3
"""Import legacy per-stock runtime JSON into SQLite and optionally remove it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.storage import MarketDataStore


SNAPSHOT_FILES = {
    "quote.json": "quote",
    "fundamentals.json": "fundamentals",
    "news.json": "news",
    "indicators.json": "indicators",
}
SUPPORTED_FILES = {"kline.json", *SNAPSHOT_FILES}


def _read(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


def _verify_bar_dates(store: MarketDataStore, code: str, records) -> bool:
    expected = {str(row.get("date", ""))[:10] for row in records if row.get("date")}
    actual = {row["date"] for row in store.load_bars(code)}
    return bool(expected) and expected <= actual


def migrate(
    root: str | Path,
    *,
    store: MarketDataStore,
    delete_after_verify: bool = False,
) -> Dict[str, Any]:
    root = Path(root)
    summary = {
        "files_scanned": 0,
        "files_imported": 0,
        "files_deleted": 0,
        "bars_seen": 0,
        "errors": [],
    }
    data_dir = root / "data"
    if not data_dir.exists():
        return summary

    for stock_dir in sorted(path for path in data_dir.iterdir() if path.is_dir()):
        code = stock_dir.name
        for filename in sorted(SUPPORTED_FILES):
            path = stock_dir / filename
            if not path.exists():
                continue
            summary["files_scanned"] += 1
            try:
                payload = _read(path)
                payload_code = str(payload.get("code") or code)
                name = str(payload.get("name") or payload_code)
                market = str(payload.get("market") or "")
                if filename == "kline.json":
                    records = payload.get("kline") or payload.get("data") or []
                    if not records:
                        raise ValueError("K-line payload contains no records")
                    source = (payload.get("_evidence") or {}).get("source", "legacy_json")
                    store.upsert_bars(payload_code, name, market, records, source=source)
                    summary["bars_seen"] += len(records)
                    verified = _verify_bar_dates(store, payload_code, records)
                else:
                    kind = SNAPSHOT_FILES[filename]
                    store.save_snapshot(payload_code, name, market, kind, payload)
                    verified = store.load_snapshot(payload_code, kind) == payload
                if not verified:
                    raise RuntimeError("database verification failed")
                summary["files_imported"] += 1
                if delete_after_verify:
                    path.unlink()
                    summary["files_deleted"] += 1
            except Exception as exc:
                summary["errors"].append({"path": str(path), "error": str(exc)})
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--delete-after-verify", action="store_true")
    args = parser.parse_args()
    database = args.database or args.root / "data/stock_analysis.db"
    summary = migrate(
        args.root,
        store=MarketDataStore(database),
        delete_after_verify=args.delete_after_verify,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
