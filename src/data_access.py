"""Application-facing access to per-stock market data stored in SQLite."""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from src.storage import MarketDataStore, get_market_store


def _store(store: Optional[MarketDataStore]) -> MarketDataStore:
    return store if store is not None else get_market_store()


def load_bars(
    code: str,
    *,
    limit: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    store: Optional[MarketDataStore] = None,
) -> Dict[str, Any]:
    rows = _store(store).load_bars(code, limit=limit, start=start, end=end)
    source = rows[-1].get("data_source", "unknown") if rows else "unknown"
    return {
        "code": code,
        "name": code,
        "kline": rows,
        "_evidence": {"source": source, "gaps": []},
    }


def load_quote(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "quote")


def load_fundamentals(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "fundamentals")


def load_news(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "news")


def load_indicators(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "indicators")


def load_research_evidence(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "research_evidence")


def load_research_summary(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "research_summary")

def load_financial_report_evidence(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "financial_report_evidence")

def load_financial_quality_summary(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "financial_quality_summary")

def load_financial_collection_status(code: str, *, store: Optional[MarketDataStore] = None):
    return _store(store).load_snapshot(code, "financial_collection_status")


def incremental_days(
    code: str,
    *,
    full_days: int = 500,
    overlap: int = 5,
    as_of: Optional[date] = None,
    store: Optional[MarketDataStore] = None,
) -> int:
    """Return the minimum trailing-day request that closes any stored gap."""
    latest = _store(store).latest_bar_date(code)
    if not latest:
        return full_days
    end = as_of or date.today()
    first_missing = date.fromisoformat(latest) + timedelta(days=1)
    gap_sessions = len(pd.bdate_range(first_missing, end)) if first_missing <= end else 0
    return min(full_days, max(overlap, gap_sessions + overlap))


def query_payload(code: str, kind: str, *, limit: Optional[int] = None, store=None):
    loaders = {
        "bars": lambda: load_bars(code, limit=limit, store=store),
        "quote": lambda: load_quote(code, store=store),
        "fundamentals": lambda: load_fundamentals(code, store=store),
        "news": lambda: load_news(code, store=store),
        "indicators": lambda: load_indicators(code, store=store),
        "research_evidence": lambda: load_research_evidence(code, store=store),
        "research_summary": lambda: load_research_summary(code, store=store),
        "financial_report_evidence": lambda: load_financial_report_evidence(code, store=store),
        "financial_quality_summary": lambda: load_financial_quality_summary(code, store=store),
        "financial_collection_status": lambda: load_financial_collection_status(code, store=store),
    }
    return loaders[kind]()


def main() -> int:
    parser = argparse.ArgumentParser(description="Read per-stock data from SQLite")
    parser.add_argument("--code", required=True)
    parser.add_argument(
        "--kind",
        required=True,
        choices=[
            "bars", "quote", "fundamentals", "news", "indicators",
            "research_evidence", "research_summary",
            "financial_report_evidence", "financial_quality_summary", "financial_collection_status",
        ],
    )
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    payload = query_payload(args.code, args.kind, limit=args.limit)
    if payload is None:
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
