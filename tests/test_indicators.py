"""Tests for src/indicators.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from unittest import mock
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.indicators import compute_indicators, _safe_float, _safe_list
from src.config import Config


def _make_mock_kline(num_days=60):
    np.random.seed(42)
    dates = pd.date_range(end="2026-06-01", periods=num_days, freq="B")
    base_price = 100.0
    trend = np.linspace(0, 10, num_days)
    noise = np.random.normal(0, 1.5, num_days)
    closes = base_price + trend + noise
    records = []
    for i in range(num_days):
        records.append({
            "date": dates[i].isoformat(),
            "open": float(closes[i] - 0.5),
            "high": float(closes[i] + 2),
            "low": float(closes[i] - 2),
            "close": float(closes[i]),
            "volume": 200000,
            "amount": float(closes[i] * 200000),
            "pct_chg": 0.0,
        })
    return {"code": "600519", "name": "贵州茅台", "market": "SH", "kline": records, "updated_at": "2026-06-01T15:30:00+08:00"}


class TestSafeHelpers:
    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_valid(self):
        assert _safe_float(3.14159) == 3.14

    def test_safe_float_string(self):
        assert _safe_float("invalid") is None

    def test_safe_list_none(self):
        assert _safe_list(None) == []

    def test_safe_list_valid(self):
        assert _safe_list([1.2, 3.4, 5.6]) == [1.2, 3.4, 5.6]


class TestComputeIndicators:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        self.stock_dir = tmp_path / "600519"
        self.stock_dir.mkdir(parents=True)
        kline_data = _make_mock_kline(60)
        with open(self.stock_dir / "kline.json", "w") as f:
            json.dump(kline_data, f, ensure_ascii=False)

    def _set_data_dir(self, path: Path):
        os.environ["DATA_DIR"] = str(path)
        Config.reset_instance()

    def test_kline_not_found(self):
        self._set_data_dir(self.tmp.parent / "nonexistent")
        result = compute_indicators("600519")
        assert result is False

    def test_produces_output(self):
        self._set_data_dir(self.tmp)
        result = compute_indicators("600519")
        assert result is True
        data = json.loads((self.stock_dir / "indicators.json").read_text())
        for key in ["code", "ma", "macd", "rsi", "volume", "bias", "trend", "buy_signal", "risk_factors"]:
            assert key in data, f"Missing key: {key}"

    def test_ma_fields(self):
        self._set_data_dir(self.tmp)
        compute_indicators("600519")
        data = json.loads((self.stock_dir / "indicators.json").read_text())
        ma = data["ma"]
        assert ma["ma5"] is not None and ma["ma10"] is not None

    def test_macd_fields(self):
        self._set_data_dir(self.tmp)
        compute_indicators("600519")
        data = json.loads((self.stock_dir / "indicators.json").read_text())
        macd = data["macd"]
        assert macd["dif"] is not None

    def test_rsi_fields(self):
        self._set_data_dir(self.tmp)
        compute_indicators("600519")
        data = json.loads((self.stock_dir / "indicators.json").read_text())
        rsi = data["rsi"]
        assert rsi["rsi6"] is not None

    def test_buy_signal(self):
        self._set_data_dir(self.tmp)
        compute_indicators("600519")
        data = json.loads((self.stock_dir / "indicators.json").read_text())
        buy = data["buy_signal"]
        assert 0 <= buy["score"] <= 100
