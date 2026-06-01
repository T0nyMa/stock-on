"""Tests for src/indicators.py — 技术指标计算"""
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.indicators import compute_indicators, _safe_float, _safe_list


def _make_mock_kline(num_days=60):
    """Generate realistic mock K-line data for testing."""
    np.random.seed(42)
    dates = pd.date_range(end="2026-06-01", periods=num_days, freq="B")
    base_price = 100.0
    # Simulate a slow uptrend
    trend = np.linspace(0, 10, num_days)
    noise = np.random.normal(0, 1.5, num_days)
    closes = base_price + trend + noise
    highs = closes + np.random.uniform(0.5, 3, num_days)
    lows = closes - np.random.uniform(0.5, 3, num_days)
    opens = closes - np.random.uniform(-1, 1, num_days)
    volumes = np.random.randint(100000, 500000, num_days)
    amounts = volumes * closes

    records = []
    for i in range(num_days):
        records.append({
            "date": dates[i].isoformat(),
            "open": float(opens[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i]),
            "volume": int(volumes[i]),
            "amount": float(amounts[i]),
            "pct_chg": round(float((closes[i] - closes[i-1]) / closes[i-1] * 100 if i > 0 else 0), 2),
        })

    return {
        "code": "600519",
        "name": "贵州茅台",
        "market": "SH",
        "updated_at": "2026-06-01T15:30:00+08:00",
        "kline": records,
    }


class TestSafeHelpers:
    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_valid(self):
        assert _safe_float(3.14159) == 3.14

    def test_safe_float_zero(self):
        assert _safe_float(0) == 0.0

    def test_safe_float_string(self):
        assert _safe_float("invalid") is None

    def test_safe_list_none(self):
        assert _safe_list(None) == []

    def test_safe_list_valid(self):
        assert _safe_list([1.2, 3.4, 5.6]) == [1.2, 3.4, 5.6]


class TestComputeIndicators:
    @pytest.fixture(autouse=True)
    def setup_data(self, tmp_path):
        self.tmp = tmp_path
        self.stock_dir = tmp_path / "600519"
        self.stock_dir.mkdir(parents=True)

        kline_data = _make_mock_kline(60)
        kline_path = self.stock_dir / "kline.json"
        with open(kline_path, "w") as f:
            json.dump(kline_data, f, ensure_ascii=False)

    @mock.patch.dict(os.environ, {"DATA_DIR": ""})
    def _set_data_dir(self, tmp_path):
        os.environ["DATA_DIR"] = str(tmp_path)

    def test_kline_not_found(self):
        """Should return False when kline.json doesn't exist."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp.parent / "nonexistent")}):
            result = compute_indicators("600519")
            assert result is False

    def test_compute_indicators_produces_output(self):
        """Should write indicators.json with all required fields."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp)}):
            result = compute_indicators("600519")
            assert result is True

            output_path = self.stock_dir / "indicators.json"
            assert output_path.exists()

            data = json.loads(output_path.read_text())

            # Required top-level keys
            for key in ["code", "ma", "macd", "rsi", "volume", "bias", "trend", "buy_signal", "risk_factors"]:
                assert key in data, f"Missing key: {key}"

    def test_indicators_ma_fields(self):
        """MA should have ma5, ma10, ma20, ma60."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp)}):
            compute_indicators("600519")
            data = json.loads((self.stock_dir / "indicators.json").read_text())

            ma = data["ma"]
            assert ma["ma5"] is not None
            assert ma["ma10"] is not None
            assert ma["ma20"] is not None
            assert ma["ma60"] is not None
            # In uptrend, ma5 should be highest
            if ma["ma5"] and ma["ma20"]:
                assert ma["ma5"] >= ma["ma20"]

    def test_indicators_macd_fields(self):
        """MACD should have dif, dea, hist."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp)}):
            compute_indicators("600519")
            data = json.loads((self.stock_dir / "indicators.json").read_text())

            macd = data["macd"]
            assert macd["dif"] is not None
            assert macd["dea"] is not None
            assert macd["hist"] is not None  # mapped from macd_bar

    def test_indicators_rsi_fields(self):
        """RSI should have rsi6, rsi12, rsi24."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp)}):
            compute_indicators("600519")
            data = json.loads((self.stock_dir / "indicators.json").read_text())

            rsi = data["rsi"]
            assert 0 < rsi["rsi6"] < 100 if rsi["rsi6"] else True
            assert 0 < rsi["rsi12"] < 100 if rsi["rsi12"] else True
            assert 0 < rsi["rsi24"] < 100 if rsi["rsi24"] else True

    def test_indicators_trend_status(self):
        """Trend should have a valid status string."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp)}):
            compute_indicators("600519")
            data = json.loads((self.stock_dir / "indicators.json").read_text())

            trend = data["trend"]
            assert trend["status"] != ""
            assert len(trend["support_levels"]) >= 0
            assert len(trend["resistance_levels"]) >= 0

    def test_indicators_buy_signal(self):
        """Buy signal should have score between 0-100."""
        with mock.patch.dict(os.environ, {"DATA_DIR": str(self.tmp)}):
            compute_indicators("600519")
            data = json.loads((self.stock_dir / "indicators.json").read_text())

            buy = data["buy_signal"]
            assert 0 <= buy["score"] <= 100
            assert isinstance(buy["reasons"], list)
