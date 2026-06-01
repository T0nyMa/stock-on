#!/usr/bin/env python3
"""
数据抓取入口。供 Claude Code fetch-data Skill 调用。

用法: python src/fetch.py --code 600519
输出: data/{code}/kline.json, quote.json, fundamentals.json, news.json

注意:
  - DataFetcherManager() 不接受 Config 参数，用无参构造自动初始化
  - SearchService() 从环境变量读取 API keys
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from src.config import get_config, setup_env
from src.data_provider import DataFetcherManager
from src.data_provider.base import canonical_stock_code

logger = logging.getLogger(__name__)

_TZ_CN = timezone(timedelta(hours=8))


def _now_str() -> str:
    return datetime.now(_TZ_CN).isoformat()


def _ensure_data_dir(code: str) -> Path:
    config = get_config()
    stock_dir = Path(config.data_dir) / code
    stock_dir.mkdir(parents=True, exist_ok=True)
    return stock_dir


def _write_json(stock_dir: Path, filename: str, data: dict):
    path = stock_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("已写入: %s", path)


def _detect_market(code: str) -> str:
    code = code.upper()
    if code.startswith("HK"):
        return "HK"
    if any(code.startswith(p) for p in ("US", "NYSE", "NASDAQ")):
        return "US"
    if code[0] in ("6", "5"):
        return "SH"
    if code[0] in ("0", "3"):
        return "SZ"
    if code[0] in ("4", "8"):
        return "BJ"
    return ""


def _convert_dates(records: list) -> list:
    """Convert pandas Timestamps to ISO strings for JSON serialization."""
    import pandas as pd
    for r in records:
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                r[k] = v.isoformat()
    return records


def fetch_stock_data(code: str):
    """抓取单只股票的完整数据"""
    setup_env()
    config = get_config()
    stock_dir = _ensure_data_dir(code)

    # DataFetcherManager 无参构造，自动按优先级初始化数据源
    fetcher = DataFetcherManager()

    # 1. 抓取 K 线（近 60 个交易日）
    logger.info("正在获取 %s K线数据...", code)
    try:
        kline = fetcher.get_daily_history(code, count=60)
        if kline is not None and not kline.empty:
            records = kline.to_dict(orient="records")
            _write_json(stock_dir, "kline.json", {
                "code": code,
                "name": fetcher.get_stock_name(code),
                "market": _detect_market(code),
                "updated_at": _now_str(),
                "kline": _convert_dates(records),
            })
        else:
            logger.warning("K线数据为空: %s", code)
    except Exception as e:
        logger.error("获取K线失败 %s: %s", code, e)

    # 2. 抓取实时行情
    logger.info("正在获取 %s 实时行情...", code)
    try:
        quote = fetcher.get_realtime_quote(code)
        if quote:
            name = getattr(quote, "name", "") or fetcher.get_stock_name(code)
            _write_json(stock_dir, "quote.json", {
                "code": code,
                "name": name,
                "price": float(getattr(quote, "price", 0) or 0),
                "pct_chg": float(getattr(quote, "pct_chg", 0) or 0),
                "volume": int(getattr(quote, "volume", 0) or 0),
                "amount": float(getattr(quote, "amount", 0) or 0),
                "turnover_rate": float(getattr(quote, "turnover_rate", 0) or 0),
                "pe": float(getattr(quote, "pe", 0) or 0),
                "pb": float(getattr(quote, "pb", 0) or 0),
                "market_cap": float(getattr(quote, "market_cap", 0) or 0),
                "updated_at": _now_str(),
            })
    except Exception as e:
        logger.error("获取行情失败 %s: %s", code, e)

    # 3. 抓取基本面
    logger.info("正在获取 %s 基本面...", code)
    try:
        fundamentals = fetcher.get_fundamentals(code)
        if fundamentals:
            _write_json(stock_dir, "fundamentals.json", {
                "code": code,
                "name": fundamentals.get("name", ""),
                "pe": fundamentals.get("pe"),
                "pb": fundamentals.get("pb"),
                "market_cap": fundamentals.get("market_cap"),
                "revenue": fundamentals.get("revenue"),
                "profit": fundamentals.get("profit"),
                "industry": fundamentals.get("industry"),
                "updated_at": _now_str(),
            })
    except Exception as e:
        logger.warning("获取基本面失败 %s: %s", code, e)

    # 4. 抓取新闻
    logger.info("正在获取 %s 新闻...", code)
    try:
        from src.search_service import SearchService
        search = SearchService()
        news = search.search_stock_news(code, days=7)
        if news:
            _write_json(stock_dir, "news.json", {
                "code": code,
                "news": news,
                "updated_at": _now_str(),
            })
    except Exception as e:
        logger.warning("获取新闻失败 %s: %s", code, e)

    logger.info("数据抓取完成: %s → %s", code, stock_dir)


def main():
    parser = argparse.ArgumentParser(description="股票数据抓取")
    parser.add_argument("--code", required=True, help="股票代码")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    code = canonical_stock_code(args.code)
    fetch_stock_data(code)


if __name__ == "__main__":
    main()
