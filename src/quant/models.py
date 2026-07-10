"""Shared input normalization and JSON serialization helpers."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_OHLC = ("open", "high", "low", "close")


def normalize_bars(records: Sequence[Mapping[str, Any]]) -> tuple[pd.DataFrame, list[str]]:
    """Return sorted, unique, numeric OHLCV bars and evidence warnings."""
    columns = ["date", *REQUIRED_OHLC, "volume", "amount"]
    frame = pd.DataFrame(list(records))
    if frame.empty:
        return pd.DataFrame(columns=columns[1:], index=pd.DatetimeIndex([], name="date")), ["empty_history"]

    for column in columns:
        if column not in frame:
            frame[column] = np.nan

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in (*REQUIRED_OHLC, "volume", "amount"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    warnings: list[str] = []
    invalid_mask = frame["date"].isna() | frame[list(REQUIRED_OHLC)].isna().any(axis=1)
    invalid_count = int(invalid_mask.sum())
    if invalid_count:
        warnings.append(f"invalid_rows:{invalid_count}")
        frame = frame.loc[~invalid_mask].copy()

    duplicate_count = int(frame.duplicated(subset="date", keep="last").sum())
    if duplicate_count:
        warnings.append(f"duplicate_dates:{duplicate_count}")
        frame = frame.drop_duplicates(subset="date", keep="last")

    missing_volume = int(frame["volume"].isna().sum())
    if missing_volume:
        warnings.append(f"volume_missing:{missing_volume}")

    frame = frame.sort_values("date", kind="stable").set_index("date")
    return frame[[*REQUIRED_OHLC, "volume", "amount"]], warnings


def evidence(
    source: str,
    gaps: Sequence[str] | None = None,
    warnings: Sequence[str] | None = None,
    quality_score: int = 100,
) -> dict[str, Any]:
    """Build minimal evidence metadata with bounded quality."""
    return {
        "source": str(source or "unknown"),
        "gaps": list(gaps or []),
        "warnings": list(warnings or []),
        "quality_score": max(0, min(100, int(quality_score))),
    }


def json_safe(value: Any) -> Any:
    """Recursively convert pandas/numpy values to strict JSON-compatible values."""
    if value is None:
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, np.ndarray, pd.Series)):
        return [json_safe(item) for item in list(value)]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
