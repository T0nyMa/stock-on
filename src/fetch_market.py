#!/usr/bin/env python3
"""
大盘指数抓取。供每日报告使用。
用法: python src/fetch_market.py
输出: data/market/index.json
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
_TZ_CN = timezone(timedelta(hours=8))

INDICES = {
    "000001": {"name": "上证指数", "market": "SH"},
    "399001": {"name": "深证成指", "market": "SZ"},
    "399006": {"name": "创业板指", "market": "SZ"},
    "000688": {"name": "科创50", "market": "SH"},
}


def fetch():
    import akshare as ak

    result = {"updated_at": datetime.now(_TZ_CN).isoformat(), "indices": {}}

    for code, info in INDICES.items():
        symbol = f"sh{code}" if info["market"] == "SH" else f"sz{code}"
        try:
            df = ak.stock_zh_index_daily(symbol=symbol)
            if df.empty:
                logger.warning("%s(%s): 无数据", info["name"], code)
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else None

            entry = {
                "code": code,
                "name": info["name"],
                "date": str(latest.get("date", "")),
                "close": round(float(latest["close"]), 2),
                "open": round(float(latest.get("open", 0)), 2),
                "high": round(float(latest.get("high", 0)), 2),
                "low": round(float(latest.get("low", 0)), 2),
                "volume": int(latest.get("volume", 0)),
                "pct_chg": round(float(latest.get("pct_chg", 0) or 0), 2) if "pct_chg" in latest else None,
            }

            if entry["pct_chg"] is None:
                entry["pct_chg"] = (
                    round((entry["close"] / float(prev["close"]) - 1) * 100, 2)
                    if prev is not None
                    else 0
                )

            # 5-day trend
            if len(df) >= 5:
                tail = df.tail(5)
                entry["ma5_close"] = round(float(tail["close"].mean()), 2)
                pct_5d = (entry["close"] / float(tail.iloc[0]["close"]) - 1) * 100
                entry["pct_5d"] = round(pct_5d, 2)
            else:
                entry["ma5_close"] = None
                entry["pct_5d"] = None

            result["indices"][code] = entry
            logger.info("%s(%s): %.2f (%+.2f%%)", info["name"], code, entry["close"], entry["pct_chg"])

        except Exception as e:
            logger.error("%s(%s) 获取失败: %s", info["name"], code, e)

    output_dir = Path("data") / "market"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    logger.info("指数数据已写入: %s", output_path)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fetch()
