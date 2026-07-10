import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.quant.pipeline import build_report_context, build_stock_snapshot, run_repository


def records(n=300):
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    return [
        {"date": d.strftime("%Y-%m-%d"), "open": 10+i*.1, "high": 10.3+i*.1,
         "low": 9.8+i*.1, "close": 10.1+i*.1, "volume": 1000+i}
        for i, d in enumerate(dates)
    ]


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
    for code in ("600000", "600001"):
        (tmp_path / f"data/{code}/kline.json").write_text(json.dumps({"code": code, "name": code, "kline": records(), "_evidence": {"source": "fixture"}}))
    (tmp_path / "tracking/tracklist.json").write_text(json.dumps({"stocks": [
        {"code": "600000", "name": "浦发银行", "tier": "core", "tags": ["银行"], "hk_code": "06000"},
        {"code": "600001", "name": "邯郸钢铁", "tier": "watch", "tags": ["黄金"]},
        {"code": "600002", "name": "缺数据股票", "tier": "watch", "tags": []},
    ]}, ensure_ascii=False))
    (tmp_path / "tracking/600000-浦发银行/position.json").write_text(json.dumps({"shares": 100, "buy_price": 20, "stop_loss": 17}))
    (tmp_path / "data/market").mkdir(parents=True)
    (tmp_path / "data/market/hk_klines.json").write_text(json.dumps({"hk06000": {"name": "浦发银行H", "kline": records()}}))
    fx = [{"date": row["date"], "rate": 0.9} for row in records()]
    (tmp_path / "data/market/fx.json").write_text(json.dumps({"HKD_CNY": fx}))
    drivers = [{"date": row["date"], "value": 100+i*.2} for i, row in enumerate(records())]
    (tmp_path / "data/market/drivers.json").write_text(json.dumps({"gold_sge": drivers}))

    result = run_repository(tmp_path, as_of="2026-07-10")

    assert result["stocks_written"] == 3
    assert (tmp_path / "data/600000/technical_snapshot.json").exists()
    assert (tmp_path / "data/600000/strategy_stats.json").exists()
    assert (tmp_path / "data/600000/cross_market.json").exists()
    assert (tmp_path / "data/600001/cross_asset.json").exists()
    missing = json.loads((tmp_path / "data/600002/technical_snapshot.json").read_text())
    assert "kline" in missing["evidence"]["gaps"]
    assert (tmp_path / "data/market/market_breadth.json").exists()
    assert (tmp_path / "data/portfolio_risk.json").exists()
    assert (tmp_path / "data/report_context.json").exists()
