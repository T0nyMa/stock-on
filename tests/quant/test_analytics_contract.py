import numpy as np
import pandas as pd

from src.quant.analytics import (
    analyze_ah_pair, analyze_portfolio, calibrate_signals, compute_breadth,
    compute_indicators, multi_timeframe_state, relative_strength,
)


def bars(n=300, start=10.0):
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    close = pd.Series(start + np.arange(n) * 0.1, index=idx)
    return pd.DataFrame({"open": close-.05, "high": close+.2, "low": close-.2,
                         "close": close, "volume": 1000+np.arange(n)}, index=idx)


def test_core_indicators_are_finite_and_complete():
    result = compute_indicators(bars())
    assert result["atr14"] > 0
    assert 0 <= result["adx14"] <= 100
    assert result["obv"] > 0
    assert {"bb_upper", "bb_lower", "mfi14", "cmf20", "realized_vol20"} <= result.keys()


def test_relative_and_timeframes_are_deterministic():
    stock, benchmark = bars(), bars(start=10.0)
    stock["close"] *= np.linspace(1, 1.2, len(stock))
    rs = relative_strength(stock, benchmark)
    assert rs["return_20"] > rs["benchmark_return_20"]
    assert multi_timeframe_state(stock)["alignment"] == "aligned_bullish"


def test_breadth_and_calibration_contracts():
    breadth = compute_breadth([
        {"code":"a", "pct_chg":2, "close":12, "ma20":10, "ma60":9, "high20":12},
        {"code":"b", "pct_chg":-1, "close":8, "ma20":9, "ma60":10, "low20":8},
    ], previous_ad_line=5)
    assert breadth["participation"]["advancers"] == 1
    assert breadth["participation"]["ad_line"] == 5
    short = calibrate_signals(bars(200), [50], horizons=(5,))
    assert short["status"] == "insufficient_data" and "win_rate" not in short


def test_ah_requires_fresh_fx_and_portfolio_risk_sums():
    a = bars(60, 20); h = bars(60, 18)
    fx = pd.Series(0.9, index=a.index)
    ah = analyze_ah_pair(a, h, fx, a.index[-1])
    assert ah["status"] == "available" and ah["premium_pct"] > 0
    positions = [{"code":"a", "shares":100, "price":20, "cost":18, "stop":17},
                 {"code":"b", "shares":100, "price":10, "cost":11, "stop":9}]
    returns = pd.DataFrame({"a":[.01,-.02,.01], "b":[0,.01,-.01]})
    risk = analyze_portfolio(positions, returns)
    assert abs(sum(risk["weights"].values())-1) < 1e-9
    assert risk["stop_stress_loss"] > 0
