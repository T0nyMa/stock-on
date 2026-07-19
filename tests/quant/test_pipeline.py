import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.quant.pipeline import build_report_context, build_stock_snapshot, run_repository
from src.storage import MarketDataStore


def records(n=300):
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    return [
        {"date": d.strftime("%Y-%m-%d"), "open": 10+i*.1, "high": 10.3+i*.1,
         "low": 9.8+i*.1, "close": 10.1+i*.1, "volume": 1000+i}
        for i, d in enumerate(dates)
    ]


def test_stock_snapshot_contains_registered_price_volume():
    records_61 = records(61)
    records_61[-1]["volume"] = 5000

    snapshot = build_stock_snapshot(
        "601899",
        "紫金矿业",
        records_61,
        source_evidence={"source": "test", "gaps": []},
        as_of="2026-07-17",
    )

    assert snapshot["price_volume"]["volume_vs_ma20"] is not None
    assert snapshot["price_volume"]["price_volume_label"] in {
        "放量上涨",
        "缩量上涨",
        "放量下跌",
        "缩量下跌",
        "正常量能",
    }


def test_stock_snapshot_preserves_unavailable_price_volume():
    snapshot = build_stock_snapshot(
        "02050", "三花智控H", [], as_of="2026-07-17"
    )

    assert snapshot["price_volume"]["volume_state"] == "unavailable"
    assert "history_lt_20" in snapshot["price_volume"]["evidence_gaps"]


def test_stock_snapshot_is_versioned_deterministic_and_json_safe():
    first = build_stock_snapshot("600000", "浦发银行", records(), {"source": "fixture"}, "2026-07-10")
    second = build_stock_snapshot("600000", "浦发银行", records(), {"source": "fixture"}, "2026-07-10")

    assert first == second
    assert first["schema_version"] == "2.0"
    assert {"indicators", "structure", "timeframes", "relative_strength", "setups", "risk_summary"} <= set(first)
    assert first["evidence"]["source"] == "fixture"
    json.dumps(first, allow_nan=False)


def test_report_context_preserves_unavailable_instead_of_neutral():
    context = build_report_context({"600000": {"evidence": {"gaps": ["benchmark"]}}}, None, None, None)

    assert context["market_breadth"]["status"] == "unavailable"
    assert context["portfolio_risk"]["status"] == "unavailable"


def test_repository_runner_writes_stock_market_strategy_and_portfolio_artifacts(tmp_path: Path):
    (tmp_path / "data/600000").mkdir(parents=True)
    (tmp_path / "data/600001").mkdir(parents=True)
    (tmp_path / "tracking/600000-浦发银行").mkdir(parents=True)
    (tmp_path / "tracking/600001-邯郸钢铁").mkdir(parents=True)
    (tmp_path / "tracking").mkdir(exist_ok=True)
    store = MarketDataStore(tmp_path / "data/stock_analysis.db")
    for code in ("600000", "600001"):
        store.upsert_bars(code, code, "SH", records(), source="fixture")
    (tmp_path / "tracking/tracklist.json").write_text(json.dumps({"stocks": [
        {"code": "600000", "name": "浦发银行", "tier": "core", "tags": ["银行"], "hk_code": "06000", "has_position": True},
        {"code": "600001", "name": "邯郸钢铁", "tier": "watch", "tags": ["黄金"]},
        {"code": "600002", "name": "缺数据股票", "tier": "watch", "tags": []},
        {"code": "09988", "name": "阿里巴巴", "tier": "key", "tags": ["港股"], "market": "HK"},
    ]}, ensure_ascii=False))
    (tmp_path / "tracking/600000-浦发银行/position.json").write_text(json.dumps({"shares": 100, "buy_price": 20, "stop_loss": 17}))
    (tmp_path / "tracking/600001-邯郸钢铁/position.json").write_text(json.dumps({"shares": 999, "buy_price": 10, "stop_loss": 8}))
    (tmp_path / "data/market").mkdir(parents=True)
    (tmp_path / "data/market/hk_klines.json").write_text(json.dumps({
        "hk06000": {"name": "浦发银行H", "kline": records()},
        "hk09988": {"name": "阿里巴巴", "kline": records()},
    }))
    fx = [{"date": row["date"], "rate": 0.9} for row in records()]
    (tmp_path / "data/market/fx.json").write_text(json.dumps({"HKD_CNY": fx}))
    drivers = [{"date": row["date"], "value": 100+i*.2} for i, row in enumerate(records())]
    (tmp_path / "data/market/drivers.json").write_text(json.dumps({"gold_sge": drivers}))

    result = run_repository(tmp_path, as_of="2026-07-10", store=store)

    assert result["stocks_written"] == 4
    assert result["positions"] == 1
    assert (tmp_path / "data/600000/technical_snapshot.json").exists()
    assert (tmp_path / "data/600000/strategy_stats.json").exists()
    assert (tmp_path / "data/600000/cross_market.json").exists()
    assert (tmp_path / "data/600001/cross_asset.json").exists()
    missing = json.loads((tmp_path / "data/600002/technical_snapshot.json").read_text())
    assert "kline" in missing["evidence"]["gaps"]
    hk = json.loads((tmp_path / "data/09988/technical_snapshot.json").read_text())
    assert "kline" not in hk["evidence"]["gaps"]
    assert (tmp_path / "data/market/market_breadth.json").exists()
    assert (tmp_path / "data/portfolio_risk.json").exists()
    assert (tmp_path / "data/report_context.json").exists()
    context = json.loads((tmp_path / "data/report_context.json").read_text())
    assert context["stocks"]["600000"]["price_volume"]["volume_vs_ma20"] is not None
    assert context["stocks"]["600002"]["price_volume"]["volume_state"] == "unavailable"
