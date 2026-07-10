"""Pure artifact builders plus a thin repository JSON orchestrator."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .analytics import (
    analyze_portfolio,
    analyze_structure,
    calibrate_signals,
    compute_breadth,
    compute_indicators,
    multi_timeframe_state,
)
from .models import evidence, json_safe, normalize_bars

SCHEMA_VERSION = "2.0"


def build_stock_snapshot(code, name, records, source_evidence=None, as_of=None, benchmark=None):
    frame, warnings = normalize_bars(records)
    source_evidence = dict(source_evidence or {})
    gaps = list(source_evidence.get("gaps", []))
    if benchmark is None:
        gaps.append("benchmark")
    if frame.empty:
        gaps.append("kline")
    ev = evidence(source_evidence.get("source", "unknown"), sorted(set(gaps)), warnings, source_evidence.get("quality_score", 100))
    indicators = compute_indicators(frame) if len(frame) else {}
    structure = analyze_structure(frame) if len(frame) >= 20 else {"status": "insufficient_data"}
    timeframes = multi_timeframe_state(frame) if len(frame) else {"states": {}, "alignment": "unavailable"}
    setup = structure.get("setup") if isinstance(structure, dict) else None
    return json_safe({
        "schema_version": SCHEMA_VERSION,
        "identity": {"code": str(code), "name": str(name)},
        "as_of": str(as_of or (frame.index[-1].date() if len(frame) else "")),
        "evidence": ev,
        "indicators": indicators,
        "structure": structure,
        "relative_strength": {"status": "unavailable", "reason": "benchmark_missing"} if benchmark is None else benchmark,
        "timeframes": timeframes,
        "setups": [setup] if setup else [],
        "risk_summary": {"atr14": indicators.get("atr14"), "natr14": indicators.get("natr14"), "realized_vol20": indicators.get("realized_vol20")},
    })


def build_report_context(stocks, breadth, cross_market, portfolio):
    unavailable = {"status": "unavailable", "reason": "artifact_missing"}
    return json_safe({
        "schema_version": SCHEMA_VERSION,
        "stocks": stocks,
        "market_breadth": breadth or unavailable,
        "cross_market": cross_market or unavailable,
        "portfolio_risk": portfolio or unavailable,
    })


def _read(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write_atomic(path: Path, value: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temporary, path)


def _position(root: Path, stock: dict, price: float):
    path = root / "tracking" / f'{stock["code"]}-{stock["name"]}' / "position.json"
    raw = _read(path, {}) or {}
    body = raw.get("position", raw)
    fallback = stock.get("position_info", {})
    shares = body.get("shares", fallback.get("shares", 0)) or 0
    if shares <= 0:
        return None
    levels = raw.get("key_levels", {})
    stop = levels.get("stop_loss")
    return {"code": stock["code"], "shares": shares, "price": price,
            "cost": body.get("buy_price", fallback.get("buy_price", 0)) or 0,
            "stop": stop if isinstance(stop, (int, float)) else price,
            "sector": (stock.get("tags") or ["unknown"])[0],
            "theme": (stock.get("tags") or ["unknown"])[-1]}


def run_repository(root: str | Path, as_of=None):
    root = Path(root)
    tracklist = _read(root / "tracking/tracklist.json", {}) or {}
    stocks = tracklist.get("stocks", [])
    snapshots = {}; frames = {}; quotes = []; positions = []
    for stock in stocks:
        code = str(stock["code"])
        raw = _read(root / f"data/{code}/kline.json", {}) or {}
        records = raw.get("kline") or raw.get("data") or []
        if not records:
            continue
        frame, _ = normalize_bars(records)
        snapshot = build_stock_snapshot(code, stock.get("name", raw.get("name", code)), records, raw.get("_evidence"), as_of)
        snapshots[code] = snapshot; frames[code] = frame
        _write_atomic(root / f"data/{code}/technical_snapshot.json", snapshot)
        ma20 = float(frame.close.tail(20).mean()) if len(frame) >= 20 else None
        ma60 = float(frame.close.tail(60).mean()) if len(frame) >= 60 else None
        pct = float(frame.close.pct_change().iloc[-1] * 100) if len(frame) > 1 else 0
        quotes.append({"code": code, "pct_chg": pct, "close": float(frame.close.iloc[-1]), "ma20": ma20, "ma60": ma60,
                       "high20": float(frame.high.tail(20).max()), "low20": float(frame.low.tail(20).min())})
        ma = frame.close.rolling(20).mean(); signals = [i for i in range(1, len(frame)) if pd.notna(ma.iloc[i-1]) and frame.close.iloc[i-1] <= ma.iloc[i-1] and frame.close.iloc[i] > ma.iloc[i]]
        stats = {"schema_version": SCHEMA_VERSION, "as_of": str(as_of or frame.index[-1].date()), "history": {"bars": len(frame)}, "strategies": {"ma20_breakout": calibrate_signals(frame, signals)}}
        _write_atomic(root / f"data/{code}/strategy_stats.json", stats)
        pos = _position(root, stock, float(frame.close.iloc[-1]))
        if pos: positions.append(pos)
    breadth = compute_breadth(quotes)
    _write_atomic(root / "data/market/market_breadth.json", breadth)
    returns = pd.concat({code: frame.close.pct_change() for code, frame in frames.items()}, axis=1) if frames else pd.DataFrame()
    portfolio = analyze_portfolio(positions, returns) if positions else {"schema_version": SCHEMA_VERSION, "status": "unavailable", "reason": "no_positions"}
    _write_atomic(root / "data/portfolio_risk.json", portfolio)
    context = build_report_context(snapshots, breadth, None, portfolio)
    _write_atomic(root / "data/report_context.json", context)
    return {"stocks_written": len(snapshots), "positions": len(positions)}
