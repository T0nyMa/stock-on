import math

import numpy as np

from src.quant.models import evidence, json_safe, normalize_bars


def test_normalize_bars_sorts_deduplicates_and_reports_warning():
    frame, warnings = normalize_bars([
        {"date": "2026-01-02", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1},
        {"date": "2026-01-01", "open": 9, "high": 10, "low": 8, "close": 9, "volume": 1},
        {"date": "2026-01-02", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 2},
    ])

    assert list(frame.index.strftime("%Y-%m-%d")) == ["2026-01-01", "2026-01-02"]
    assert frame.iloc[-1]["close"] == 11
    assert warnings == ["duplicate_dates:1"]


def test_normalize_bars_removes_invalid_ohlc_rows_but_allows_missing_volume():
    frame, warnings = normalize_bars([
        {"date": "2026-01-01", "open": 9, "high": 10, "low": 8, "close": 9},
        {"date": "2026-01-02", "open": 9, "high": None, "low": 8, "close": 9, "volume": 1},
    ])

    assert len(frame) == 1
    assert math.isnan(frame.iloc[0]["volume"])
    assert warnings == ["invalid_rows:1", "volume_missing:1"]


def test_json_safe_replaces_non_finite_and_numpy_scalars():
    value = json_safe({"a": float("nan"), "b": float("inf"), "c": np.int64(3)})
    assert value == {"a": None, "b": None, "c": 3}


def test_evidence_clamps_quality_and_copies_lists():
    gaps = ["volume"]
    result = evidence("tencent", gaps, ["stale"], 120)
    gaps.append("fx")

    assert result == {
        "source": "tencent",
        "gaps": ["volume"],
        "warnings": ["stale"],
        "quality_score": 100,
    }
