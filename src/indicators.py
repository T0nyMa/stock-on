#!/usr/bin/env python3
"""
技术指标计算入口。供 Claude Code tech-indicators Skill 调用。

用法: python src/indicators.py --code 600519
输入: data/{code}/kline.json
输出: data/{code}/indicators.json

依赖: StockTrendAnalyzer.analyze(df, code) → TrendAnalysisResult
字段映射参见 ref-repo/src/stock_analyzer.py:135-168 TrendAnalysisResult.to_dict()
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import get_config
from src.stock_analyzer import StockTrendAnalyzer

logger = logging.getLogger(__name__)


def _safe_float(val):
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


def _safe_list(val):
    if val is None:
        return []
    return [round(float(v), 2) if v else 0 for v in val]


def compute_indicators(code: str):
    """计算技术指标并写入 JSON"""
    config = get_config()
    stock_dir = Path(config.data_dir) / code
    kline_path = stock_dir / "kline.json"

    if not kline_path.exists():
        logger.error("K线数据不存在: %s", kline_path)
        return False

    with open(kline_path, "r", encoding="utf-8") as f:
        kline_data = json.load(f)

    import pandas as pd
    df = pd.DataFrame(kline_data["kline"])
    if df.empty:
        logger.error("K线为空: %s", code)
        return False

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # StockTrendAnalyzer 接口: analyze(df, code) → TrendAnalysisResult
    analyzer = StockTrendAnalyzer()
    result = analyzer.analyze(df, code)

    # 字段名严格对应 TrendAnalysisResult (ref-repo/src/stock_analyzer.py:83-168)
    ma5_vol = None
    if len(df) >= 5:
        vol_tail = df["volume"].tail(5)
        if not vol_tail.empty:
            ma5_vol = round(float(vol_tail.mean()), 2)

    indicators = {
        "code": code,
        "updated_at": kline_data.get("updated_at", ""),
        "ma": {
            "ma5": _safe_float(result.ma5),
            "ma10": _safe_float(result.ma10),
            "ma20": _safe_float(result.ma20),
            "ma60": _safe_float(result.ma60),
        },
        "macd": {
            "dif": _safe_float(result.macd_dif),
            "dea": _safe_float(result.macd_dea),
            "hist": _safe_float(result.macd_bar),  # TrendAnalysisResult 中名为 macd_bar
        },
        "rsi": {
            "rsi6": _safe_float(result.rsi_6),
            "rsi12": _safe_float(result.rsi_12),
            "rsi24": _safe_float(result.rsi_24),
        },
        "volume": {
            "ma5_vol": ma5_vol,
            "volume_ratio": _safe_float(result.volume_ratio_5d),
            "volume_status": getattr(result.volume_status, "value", "")
            if hasattr(result.volume_status, "value") else str(result.volume_status),
        },
        "bias": {
            "bias5": _safe_float(result.bias_ma5),
            "bias10": _safe_float(result.bias_ma10),
            "bias20": _safe_float(result.bias_ma20),
        },
        "trend": {
            "status": getattr(result.trend_status, "value", "")
            if hasattr(result.trend_status, "value") else str(result.trend_status),
            "ma_alignment": getattr(result, "ma_alignment", ""),
            "trend_strength": _safe_float(getattr(result, "trend_strength", 0)),
            "support_levels": _safe_list(result.support_levels),
            "resistance_levels": _safe_list(result.resistance_levels),
        },
        "buy_signal": {
            "signal": getattr(result.buy_signal, "value", "")
            if hasattr(result.buy_signal, "value") else str(result.buy_signal),
            "score": int(getattr(result, "signal_score", 0) or 0),
            "reasons": list(getattr(result, "signal_reasons", []) or []),
        },
        "risk_factors": list(getattr(result, "risk_factors", []) or []),
    }

    output_path = stock_dir / "indicators.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(indicators, f, ensure_ascii=False, indent=2, default=str)
    logger.info("技术指标已写入: %s", output_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="技术指标计算")
    parser.add_argument("--code", required=True, help="股票代码")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    compute_indicators(args.code)


if __name__ == "__main__":
    main()
