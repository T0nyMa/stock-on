import numpy as np
import pandas as pd

from src.quant.analytics import (
    analyze_cross_asset,
    analyze_portfolio,
    analyze_structure,
    calibrate_signals,
    rank_relative_strength,
)


def make_bars(closes):
    index = pd.date_range("2024-01-01", periods=len(closes), freq="B")
    close = pd.Series(closes, index=index, dtype=float)
    return pd.DataFrame(
        {
            "open": close.shift().fillna(close.iloc[0]),
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1000.0,
        },
        index=index,
    )


def test_structure_finds_levels_gaps_profile_and_actionable_setup():
    closes = np.r_[np.linspace(10, 15, 30), np.linspace(15, 11, 20), np.linspace(11, 16, 40)]
    frame = make_bars(closes)
    frame.iloc[55:, frame.columns.get_loc("low")] += 1.0
    frame.iloc[55:, frame.columns.get_loc("high")] += 1.0
    frame.iloc[55:, frame.columns.get_loc("open")] += 1.0
    frame.iloc[55:, frame.columns.get_loc("close")] += 1.0

    result = analyze_structure(frame)

    assert result["supports"]
    assert result["resistances"]
    assert len(result["volume_profile"]) == 20
    assert abs(sum(item["volume"] for item in result["volume_profile"]) - frame.volume.sum()) < 1e-6
    assert "anchored_vwap" in result
    assert result["setup"]["risk_reward"] >= 1.5


def test_calibration_has_mae_mfe_payoff_and_cooldown():
    frame = make_bars(np.linspace(10, 40, 300) + np.sin(np.arange(300)))
    result = calibrate_signals(frame, [100, 101, 102, 150], horizons=(5,))
    stats = result["horizons"]["5"]

    assert stats["sample_size"] == 2
    assert {"mae", "mfe", "payoff_ratio", "expected_return"} <= stats.keys()


def test_relative_strength_ranking_includes_ties():
    assert rank_relative_strength({"a": 3, "b": 1, "c": 1}) == {"a": 100.0, "b": 25.0, "c": 25.0}


def test_cross_asset_detects_driver_leading_stock():
    idx = pd.date_range("2025-01-01", periods=100, freq="B")
    driver = pd.Series(np.sin(np.arange(100) / 5) + np.arange(100) / 50, index=idx)
    stock = driver.shift(2).dropna()

    result = analyze_cross_asset(stock, driver, windows=(20, 60), max_lag=5)

    assert result["status"] == "available"
    assert result["best_lag"] == 2
    assert result["lead_lag_correlations"]["2"] > 0.99


def test_portfolio_component_risk_and_exposures():
    positions = [
        {"code": "a", "shares": 100, "price": 20, "cost": 18, "stop": 17, "sector": "AI", "theme": "算力"},
        {"code": "b", "shares": 100, "price": 10, "cost": 11, "stop": 9, "sector": "黄金", "theme": "避险"},
    ]
    returns = pd.DataFrame({"a": [.01, -.02, .01, .03], "b": [0, .01, -.01, .02]})

    result = analyze_portfolio(positions, returns)

    assert set(result["component_risk"]) == {"a", "b"}
    assert abs(sum(result["component_risk"].values()) - result["annualized_volatility"]) < 1e-9
    assert result["sector_exposure"]["AI"] == result["weights"]["a"]
