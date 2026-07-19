from datetime import date, timedelta

import pytest

from src.daily_metrics import derive_daily_metrics


def make_bars(count, *, latest_volume=240, rising=True):
    start = date(2026, 1, 1)
    bars = []
    for index in range(count):
        close = 10 + index * 0.1 if rising else 20 - index * 0.1
        bars.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": close - 0.05,
                "high": close + 0.10,
                "low": close - 0.10,
                "close": close,
                "volume": 100,
                "amount": close * 100,
            }
        )
    bars[-1]["volume"] = latest_volume
    return bars


def test_preserves_legacy_metric_contract():
    bars = make_bars(7, latest_volume=200)
    bars[-2]["volume"] = 50
    bars[-2]["amount"] = 1000
    bars[-1].update({"amount": 1500, "high": 11.0, "low": 10.0, "close": 10.75})

    result = derive_daily_metrics(bars)

    assert result["volume_ratio_5d"] == 2.22
    assert result["volume_change_vs_prev"] == 3.0
    assert result["amount_change_vs_prev"] == 0.5
    assert result["amplitude"] == 0.1
    assert result["close_position"] == 0.75
    assert result["price_change_pct"] == 2.38


def test_legacy_metrics_are_nullable_for_empty_or_insufficient_data():
    expected = {
        "volume_ratio_5d": None,
        "volume_change_vs_prev": None,
        "amount_change_vs_prev": None,
        "amplitude": None,
        "close_position": None,
    }
    assert {key: derive_daily_metrics([])[key] for key in expected} == expected
    assert {
        key: derive_daily_metrics([{"close": 10, "volume": 0}])[key] for key in expected
    } == expected


def test_classifies_expanding_up_day_and_fund_flow_confirmation():
    result = derive_daily_metrics(
        make_bars(61, latest_volume=500),
        indicators={"mfi14": 62.5, "cmf20": 0.08, "obv_series": list(range(61))},
        quote={"volume_ratio": 1.8, "turnover_rate": 2.4},
    )
    assert result["volume_state"] == "expanding"
    assert result["price_volume_label"] == "放量上涨"
    assert result["volume_vs_ma20"] >= 1.20
    assert result["mfi14"] == 62.5
    assert result["cmf20"] == 0.08
    assert result["obv_20d_direction"] == "rising"
    assert result["intraday_volume_ratio"] == 1.8
    assert result["turnover_rate"] == 2.4
    assert "positive_flow_confirmation" in result["interpretation_flags"]


def test_labels_local_expansion_inside_medium_term_contraction():
    bars = make_bars(40, latest_volume=150)
    for item in bars[:20]:
        item["volume"] = 300
    result = derive_daily_metrics(bars)
    assert result["volume_vs_ma5"] >= 1.20
    assert result["recent20_vs_previous20"] <= 0.80
    assert "local_expansion_medium_contraction" in result["interpretation_flags"]


def test_returns_unavailable_instead_of_guessing():
    result = derive_daily_metrics([{"date": "2026-07-17", "close": 10, "volume": 0}])
    assert result["volume_vs_ma20"] is None
    assert result["recent20_vs_previous20"] is None
    assert result["obv_20d_direction"] == "unavailable"
    assert result["volume_state"] == "unavailable"
    assert "history_lt_20" in result["evidence_gaps"]


@pytest.mark.parametrize(
    ("count", "has_ma5", "has_ma20", "has_comparison"),
    [
        (1, False, False, False),
        (5, True, False, False),
        (20, True, True, False),
        (39, True, True, False),
        (40, True, True, True),
    ],
)
def test_history_boundaries(count, has_ma5, has_ma20, has_comparison):
    result = derive_daily_metrics(make_bars(count))
    assert (result["volume_vs_ma5"] is not None) is has_ma5
    assert (result["volume_vs_ma20"] is not None) is has_ma20
    assert (result["recent20_vs_previous20"] is not None) is has_comparison


def test_zero_volume_denominators_and_non_numeric_inputs_are_unavailable():
    bars = make_bars(40)
    for bar in bars:
        bar["volume"] = 0
    result = derive_daily_metrics(
        bars,
        indicators={"mfi14": True, "cmf20": float("inf")},
        quote={"volume_ratio": "bad", "turnover_rate": False},
    )
    assert result["volume_vs_ma5"] is None
    assert result["volume_vs_ma20"] is None
    assert result["recent20_vs_previous20"] is None
    assert result["mfi14"] is None
    assert result["cmf20"] is None
    assert result["intraday_volume_ratio"] is None
    assert result["turnover_rate"] is None


@pytest.mark.parametrize("rising", [True, False])
def test_up_down_ratio_requires_both_up_and_down_days(rising):
    assert derive_daily_metrics(make_bars(61, rising=rising))[
        "up_down_volume_ratio_90d"
    ] is None


def test_up_down_ratio_uses_only_natural_day_window():
    bars = make_bars(100)
    bars[20]["close"] = bars[19]["close"] - 1
    bars[-1]["close"] = bars[-2]["close"] - 1
    bars[-1]["volume"] = 200
    result = derive_daily_metrics(bars, window_days=30)
    assert result["up_down_volume_ratio_90d"] is not None


def test_expanding_down_day_with_negative_cmf_is_negative_structure():
    bars = make_bars(61, latest_volume=500, rising=False)
    result = derive_daily_metrics(
        bars,
        indicators={
            "cmf20": -0.12,
            "mfi14": 25,
            "obv_series": list(range(61, 0, -1)),
        },
    )
    assert result["price_change_pct"] < 0
    assert result["price_volume_label"] == "放量下跌"
    assert result["obv_20d_direction"] == "falling"
    assert "negative_flow_confirmation" in result["interpretation_flags"]


def test_flat_obv_and_flat_price_are_neutral():
    bars = make_bars(21)
    bars[-1]["close"] = bars[-2]["close"]
    result = derive_daily_metrics(bars, indicators={"obv_series": [10] * 21})
    assert result["obv_20d_direction"] == "flat"
    assert result["price_volume_label"] == "正常量能/量价中性"


def test_scalar_obv_is_not_reconstructed_and_json_values_are_rounded():
    result = derive_daily_metrics(
        make_bars(21),
        indicators={"obv": 12345, "mfi14": 62.555},
        quote={"turnover_rate": 2.444},
    )
    assert result["obv_20d_direction"] == "unavailable"
    assert result["mfi14"] == 62.55
    assert result["turnover_rate"] == 2.44
