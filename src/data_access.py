"""Application-facing access to per-stock market data stored in SQLite."""

from __future__ import annotations

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
