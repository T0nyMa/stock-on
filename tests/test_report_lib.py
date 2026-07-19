from datetime import date, timedelta

from src import report_lib


def _bars(count=20):
    start = date(2026, 1, 1)
    result = []
    for index in range(count):
        close = 10 + index * 0.1
        result.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "open": close - 0.05,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 100,
                "amount": close * 100,
            }
        )
    result[-1]["volume"] = 500
    return result


def test_load_all_stocks_exposes_daily_metrics_and_preserves_legacy_fields(
    monkeypatch,
):
    indicator_snapshot = {
        "trend": {"status": "多头排列", "trend_strength": 80},
        "rsi": {"rsi6": 60, "rsi12": 58},
        "bias": {"bias5": 2.0},
        "macd": {"hist": 0.2},
        "ma": {"ma5": 11.7, "ma10": 11.5, "ma20": 11.0},
        "mfi14": 62.5,
        "cmf20": 0.08,
    }
    quote = {"price": 11.9, "pct_chg": 1.2, "turnover_rate": 2.4}
    fundamentals = {"pe": 25, "pb": 3, "market_cap_yi": 500}
    bars = _bars()

    monkeypatch.setattr(
        report_lib,
        "load_tracklist",
        lambda: {
            "stocks": [
                {
                    "code": "002050",
                    "name": "三花智控",
                    "tier": "core",
                    "has_position": True,
                }
            ]
        },
    )
    monkeypatch.setattr(
        report_lib,
        "load_stock_data",
        lambda code, store=None: (indicator_snapshot, quote, fundamentals),
    )
    monkeypatch.setattr(
        report_lib,
        "load_bars",
        lambda code, store=None: {"kline": bars},
    )

    stock = report_lib.load_all_stocks()[0]

    assert stock["volume_vs_ma20"] == 4.17
    assert stock["price_volume_label"] == "放量上涨"
    assert stock["mfi14"] == indicator_snapshot["mfi14"]
    assert stock["cmf20"] == indicator_snapshot["cmf20"]
    assert {
        "volume_ratio_5d",
        "volume_change_vs_prev",
        "amount_change_vs_prev",
        "amplitude",
        "close_position",
    } <= stock.keys()
