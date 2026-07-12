#!/usr/bin/env python3
"""
数据抓取入口。供 Codex 的 fetch-data Skill 调用。
用法: python src/fetch.py --code 600519
输出: SQLite（默认 data/stock_analysis.db）
"""

# Bypass macOS system proxy BEFORE any HTTP library import
import os as _os
_os.environ['no_proxy'] = '*'
try:
    import _scproxy
    _scproxy._get_proxy_settings = lambda: {}
    _scproxy._get_proxies = lambda: {}
except ImportError:
    pass

import argparse
import logging
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import get_config, setup_env
from src.data_provider import DataFetcherManager
from src.data_provider.base import canonical_stock_code
from src.providers import KlineProvider, QuoteProvider, EvidenceMeta
from src.data_access import incremental_days, load_fundamentals
from src.storage import MarketDataStore, get_market_store

logger = logging.getLogger(__name__)

_TZ_CN = timezone(timedelta(hours=8))


def _now_str() -> str:
    return datetime.now(_TZ_CN).isoformat()


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
    import pandas as pd
    for r in records:
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                r[k] = v.isoformat()
    return records


def _write_fundamentals(store: MarketDataStore, code: str, name: str, market: str):
    """写入基本面快照，空值保留数据库中的已有有效数据。"""
    import urllib.request, ssl
    ssl._create_default_https_context = ssl._create_unverified_context

    fund = {"code": code, "name": name}

    # 1. Try current fetcher first
    try:
        fetcher = DataFetcherManager()
        ctx = fetcher.get_fundamental_context(code)
        if ctx:
            fund.update({k: ctx.get(k) for k in ["pe", "pb", "market_cap", "revenue", "profit", "industry"]})
    except Exception:
        pass

    # 2. If PE/PB still null, try Tencent API
    if fund.get("pe") is None or fund.get("pb") is None:
        try:
            prefix = "sh" if code.startswith("6") else "sz"
            url = f"https://qt.gtimg.cn/q={prefix}{code}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0", "Referer": "https://finance.qq.com/",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("gbk")
            fields = raw.split('="')[1].rstrip('";\n').split('~') if '="' in raw else raw.split('=')[1].split('~')
            def _f(i, cast=float):
                if i >= len(fields) or fields[i] == '': return None
                try: return cast(fields[i])
                except: return None
            tencent = {
                "pe": _f(39), "pb": _f(46),
                "market_cap": _f(45, float),  # 亿 → 保持原始单位
                "price": _f(3), "turnover_rate": _f(38), "volume_ratio": _f(49),
                "source": "tencent",
            }
            for k in ["pe", "pb", "market_cap", "price", "turnover_rate", "volume_ratio"]:
                if fund.get(k) is None and tencent.get(k) is not None:
                    fund[k] = tencent[k]
            if tencent.get("source"):
                fund["source"] = tencent["source"]
            logger.info("[基本面] %s 从腾讯接口补充PE/PB", code)
        except Exception as e:
            logger.debug("[基本面] 腾讯接口补充失败 %s: %s", code, e)

    existing = load_fundamentals(code, store=store) or {}
    for k in ["pe", "pb", "market_cap", "revenue", "profit", "roe", "eps", "industry"]:
        if fund.get(k) is None and existing.get(k) is not None:
            fund[k] = existing[k]

    fund["updated_at"] = _now_str()
    store.save_snapshot(code, name, market, "fundamentals", fund)
    return fund


def fetch_stock_data(
    code: str,
    provider: str = "v1",
    days: int = 500,
    *,
    store: MarketDataStore | None = None,
    include_context: bool = True,
    full_refresh: bool = False,
):
    setup_env()
    store = store or get_market_store()
    requested_days = days if full_refresh else incremental_days(
        code, full_days=days, overlap=5, store=store
    )

    if provider == "v2":
        return _fetch_stock_data_v2(
            code, store, days=requested_days, include_context=include_context
        )

    fetcher = DataFetcherManager()
    market = _detect_market(code)
    name = code
    rows_received = 0

    # 1. K-line
    logger.info("正在获取 %s K线数据...", code)
    try:
        kline = fetcher.get_daily_data(code, days=requested_days)
        if isinstance(kline, tuple):
            kline = kline[0]
        if kline is not None and hasattr(kline, 'empty') and not kline.empty:
            records = kline.to_dict(orient="records")
            name = fetcher.get_stock_name(code) or code
            rows_received = len(records)
            store.upsert_bars(code, name, market, _convert_dates(records), source="v1")
    except Exception as e:
        logger.error("获取K线失败 %s: %s", code, e)
        store.record_fetch_run(code=code, provider="v1", requested_days=requested_days,
                               rows_received=0, status="failed", error=str(e))
        raise

    # 2. Realtime quote
    logger.info("正在获取 %s 实时行情...", code)
    try:
        quote = fetcher.get_realtime_quote(code)
        if quote:
            name = getattr(quote, "name", "") or fetcher.get_stock_name(code)
            payload = {
                "code": code, "name": name,
                "price": float(getattr(quote, "price", 0) or 0),
                "pct_chg": float(getattr(quote, "change_pct", 0) or 0),
                "volume": int(getattr(quote, "volume", 0) or 0),
                "amount": float(getattr(quote, "amount", 0) or 0),
                "turnover_rate": float(getattr(quote, "turnover_rate", 0) or 0),
                "pe": float(getattr(quote, "pe", 0) or 0),
                "pb": float(getattr(quote, "pb", 0) or 0),
                "market_cap": float(getattr(quote, "market_cap", 0) or 0),
                "updated_at": _now_str(),
            }
            store.save_snapshot(code, name, market, "quote", payload)
    except Exception as e:
        logger.error("获取行情失败 %s: %s", code, e)

    # 3. Fundamentals — preserve existing valid data, supplement with Tencent API
    if include_context:
        logger.info("正在获取 %s 基本面...", code)
        _write_fundamentals(store, code, name or code, market)

    # 4. News
        logger.info("正在获取 %s 新闻...", code)
        try:
            from src.search_service import SearchService
            search = SearchService()
            news = search.search_stock_news(code, name or code)
            if news:
                store.save_snapshot(code, name, market, "news", {"code": code, "news": news, "updated_at": _now_str()})
        except Exception as e:
            logger.warning("获取新闻失败 %s: %s", code, e)

    store.record_fetch_run(code=code, provider="v1", requested_days=requested_days,
                           rows_received=rows_received, status="success")
    logger.info("数据抓取完成: %s → SQLite", code)


def _fetch_stock_data_v2(
    code: str,
    store: MarketDataStore,
    days: int = 500,
    *,
    include_context: bool = True,
):
    """V2 路径: 使用 providers 直连腾讯/东财 HTTP API。"""
    kp = KlineProvider()
    qp = QuoteProvider()
    market = _detect_market(code)

    # 1. K-line
    logger.info("[V2] 正在获取 %s K线...", code)
    name = code
    rows_received = 0
    try:
        rows, k_evidence = kp.get_daily(code, limit=days)
        if rows:
            name = code  # 行情获取时更新
            kline_records = []
            for r in rows:
                kline_records.append({
                    "date": r.date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "amount": r.amount,
                    "pct_chg": r.pct_chg,
                })
            rows_received = len(kline_records)
            source = getattr(k_evidence, "source", "v2")
            store.upsert_bars(code, name, market, kline_records, source=source)
    except Exception as e:
        logger.error("[V2] 获取K线失败 %s: %s", code, e)
        store.record_fetch_run(code=code, provider="v2", requested_days=days,
                               rows_received=0, status="failed", error=str(e))
        raise

    # 2. Realtime quote
    logger.info("[V2] 正在获取 %s 行情...", code)
    try:
        q = qp.get_realtime(code)
        if q and q.price > 0:
            name = q.name or name
            payload = {
                "code": code, "name": name,
                "price": q.price,
                "pct_chg": q.change_pct,
                "volume": int(q.volume),
                "amount": q.amount,
                "turnover_rate": q.turnover_rate,
                "pe": q.pe,
                "pb": q.pb,
                "market_cap": q.market_cap,
                "updated_at": _now_str(),
                "_evidence": EvidenceMeta(source=q.source, source_chain=q.source_chain).to_dict(),
            }
            store.save_snapshot(code, name, market, "quote", payload)
    except Exception as e:
        logger.error("[V2] 获取行情失败 %s: %s", code, e)

    # 3. Fundamentals
    if include_context:
        logger.info("[V2] 正在获取 %s 基本面...", code)
        _write_fundamentals(store, code, name, market)

    # 4. News (same as V1)
        logger.info("[V2] 正在获取 %s 新闻...", code)
        try:
            from src.search_service import SearchService
            search = SearchService()
            news = search.search_stock_news(code, name)
            if news:
                store.save_snapshot(code, name, market, "news", {"code": code, "news": news, "updated_at": _now_str()})
        except Exception as e:
            logger.warning("[V2] 获取新闻失败 %s: %s", code, e)

    store.record_fetch_run(code=code, provider="v2", requested_days=days,
                           rows_received=rows_received, status="success")
    logger.info("[V2] 数据抓取完成: %s → SQLite", code)


def main():
    parser = argparse.ArgumentParser(description="股票数据抓取")
    parser.add_argument("--code", required=True, help="股票代码")
    parser.add_argument("--provider", default="v1", choices=["v1", "v2"],
                        help="数据源: v1=TickFlow+akshare(默认), v2=腾讯/东财直连")
    parser.add_argument("--days", type=int, default=500,
                        help="首次初始化K线交易日数量，默认500")
    parser.add_argument("--full-refresh", action="store_true",
                        help="强制请求完整窗口；默认仅增量补最近数据")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    code = canonical_stock_code(args.code)
    fetch_stock_data(code, provider=args.provider, days=args.days, full_refresh=args.full_refresh)


if __name__ == "__main__":
    main()
