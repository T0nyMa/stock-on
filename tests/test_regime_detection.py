"""TDD Green-phase: test market regime detection."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.regime import detect_regime, STRATEGY_MAP


# ---------------------------------------------------------------------------
# Helper: build a minimal indicators dict
# ---------------------------------------------------------------------------
def _indicators(ma_alignment="", volume_ratio=1.0, trend_strength=0.0):
    return {
        "code": "600519",
        "updated_at": "2025-01-01",
        "ma": {"ma5": 100, "ma10": 95, "ma20": 90, "ma60": 85},
        "macd": {"dif": 1.0, "dea": 0.8, "hist": 0.2},
        "rsi": {"rsi6": 60, "rsi12": 55, "rsi24": 50},
        "volume": {
            "ma5_vol": 100000,
            "volume_ratio": volume_ratio,
            "volume_status": "normal",
        },
        "bias": {"bias5": 2.0, "bias10": 3.0, "bias20": 5.0},
        "trend": {
            "status": "up",
            "ma_alignment": ma_alignment,
            "trend_strength": trend_strength,
            "support_levels": [90],
            "resistance_levels": [110],
        },
        "buy_signal": {"signal": "buy", "score": 70, "reasons": []},
        "risk_factors": [],
    }


# ---------------------------------------------------------------------------
# Unit tests: regime detection logic
# ---------------------------------------------------------------------------

def test_detect_trending_up():
    """MA5 > MA10 > MA20 alignment should yield trending_up."""
    ind = _indicators(ma_alignment="MA5>MA10>MA20")
    result = detect_regime(ind)
    assert result["regime"] == "trending_up"
    assert result["strategies"] == STRATEGY_MAP["trending_up"]
    assert 0.0 <= result["confidence"] <= 1.0


def test_detect_bearish():
    """MA5 < MA10 < MA20 alignment should yield bearish."""
    ind = _indicators(ma_alignment="MA5<MA10<MA20", trend_strength=-0.7)
    result = detect_regime(ind)
    assert result["regime"] == "bearish"
    assert result["strategies"] == STRATEGY_MAP["bearish"]


def test_detect_sector_hot_overrides_trending_up():
    """sector_hot (volume_ratio > 2.0) overrides trending_up alignment."""
    ind = _indicators(ma_alignment="MA5>MA10>MA20", volume_ratio=3.5)
    result = detect_regime(ind)
    assert result["regime"] == "sector_hot"
    assert result["strategies"] == STRATEGY_MAP["sector_hot"]
    assert "dragon_head" in result["strategies"]


def test_detect_sector_hot_overrides_bearish():
    """sector_hot overrides even a bearish alignment."""
    ind = _indicators(ma_alignment="MA5<MA10<MA20", volume_ratio=2.5)
    result = detect_regime(ind)
    assert result["regime"] == "sector_hot"


def test_default_volatile_when_no_clear_direction():
    """Without a clear MA alignment or volume spike, default to volatile."""
    ind = _indicators(ma_alignment="CHAOS", volume_ratio=1.0)
    result = detect_regime(ind)
    assert result["regime"] == "volatile"
    assert result["strategies"] == STRATEGY_MAP["volatile"]


def test_volatile_when_ma_alignment_is_empty():
    """Empty ma_alignment string should default to volatile."""
    ind = _indicators(ma_alignment="", volume_ratio=1.0)
    result = detect_regime(ind)
    assert result["regime"] == "volatile"


def test_confidence_trending_up_above_05():
    """trending_up with positive trend_strength gets confidence > 0.5."""
    ind = _indicators(ma_alignment="MA5>MA10>MA20", trend_strength=0.8)
    result = detect_regime(ind)
    assert result["confidence"] > 0.5


def test_confidence_sector_hot_above_05():
    """sector_hot confidence rises with volume_ratio."""
    ind = _indicators(volume_ratio=3.0)
    result = detect_regime(ind)
    assert result["regime"] == "sector_hot"
    assert result["confidence"] > 0.5


# ---------------------------------------------------------------------------
# Integration test: full indicators.json-like dict
# ---------------------------------------------------------------------------

def test_integration_with_real_indicators_structure():
    """Feed a realistic indicators dict (matching the compute_indicators
    output shape) and verify the correct regime is detected."""
    # Simulate a typical trending-up market with moderate volume
    real_indicators = {
        "code": "600519",
        "updated_at": "2025-06-01T12:00:00",
        "ma": {"ma5": 1850.0, "ma10": 1820.0, "ma20": 1780.0, "ma60": 1700.0},
        "macd": {"dif": 15.0, "dea": 10.0, "hist": 5.0},
        "rsi": {"rsi6": 62.0, "rsi12": 58.0, "rsi24": 54.0},
        "volume": {
            "ma5_vol": 2500000.0,
            "volume_ratio": 1.2,
            "volume_status": "normal",
        },
        "bias": {"bias5": 2.5, "bias10": 4.0, "bias20": 7.0},
        "trend": {
            "status": "up",
            "ma_alignment": "MA5>MA10>MA20",
            "trend_strength": 0.75,
            "support_levels": [1750.0, 1700.0],
            "resistance_levels": [1900.0],
        },
        "buy_signal": {
            "signal": "buy",
            "score": 85,
            "reasons": ["ma_golden_cross", "volume_rise"],
        },
        "risk_factors": ["market_volatility"],
    }

    result = detect_regime(real_indicators)

    assert result["regime"] == "trending_up"
    assert set(STRATEGY_MAP["trending_up"]).issubset(set(result["strategies"]))
    assert result["confidence"] > 0.5


def test_integration_sector_hot_with_real_structure():
    """High volume_ratio triggers sector_hot regardless of alignment."""
    real_indicators = {
        "code": "000001",
        "updated_at": "2025-06-01T12:00:00",
        "ma": {"ma5": 12.0, "ma10": 12.5, "ma20": 13.0, "ma60": 14.0},
        "macd": {"dif": -0.3, "dea": -0.2, "hist": -0.1},
        "rsi": {"rsi6": 35.0, "rsi12": 38.0, "rsi24": 42.0},
        "volume": {
            "ma5_vol": 8000000.0,
            "volume_ratio": 3.2,
            "volume_status": "surge",
        },
        "bias": {"bias5": -3.0, "bias10": -5.0, "bias20": -8.0},
        "trend": {
            "status": "down",
            "ma_alignment": "MA5<MA10<MA20",
            "trend_strength": -0.6,
            "support_levels": [11.0],
            "resistance_levels": [13.5, 14.0],
        },
        "buy_signal": {"signal": "sell", "score": 20, "reasons": []},
        "risk_factors": ["bearish_trend"],
    }

    result = detect_regime(real_indicators)

    # sector_hot overrides bearish alignment
    assert result["regime"] == "sector_hot"
    assert "hot_theme" in result["strategies"]
    assert "dragon_head" in result["strategies"]
    assert result["confidence"] > 0.5
