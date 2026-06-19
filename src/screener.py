#!/usr/bin/env python3
"""
全市场股票筛选器。基于新浪财经实时行情（通过 akshare）。
用法: python src/screener.py
输出: data/market/hot_stocks.json
"""

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
_TZ_CN = timezone(timedelta(hours=8))


def fetch_all_stocks():
    """拉取全市场实时行情"""
    import akshare as ak

    df = ak.stock_zh_a_spot()
    df = df.rename(columns={
        "代码": "code", "名称": "name",
        "最新价": "price", "涨跌额": "change", "涨跌幅": "pct_chg",
        "昨收": "prev_close", "今开": "open", "最高": "high", "最低": "low",
        "成交量": "volume", "成交额": "amount",
    })

    # 过滤：排除北交所(8开头)、ST、新股(N/C字头)
    df = df[~df["code"].str.startswith(("8", "9"))]  # 排除北交所/新三板
    df = df[~df["name"].str.contains("ST|退|N|C", na=False)]

    # 类型转换
    for col in ["price", "pct_chg", "volume", "amount", "high", "low", "prev_close"]:
        df[col] = df[col].astype(float)

    return df


def screen(df):
    """多维度筛选"""
    results = {
        "updated_at": datetime.now(_TZ_CN).isoformat(),
        "total_stocks": len(df),
        "screens": {},
    }

    # 1. 涨幅榜（排除涨停，找强势股）
    gainers = df[(df["pct_chg"] > 3) & (df["pct_chg"] < 9.5)]
    gainers = gainers.nlargest(30, "pct_chg")
    results["screens"]["top_gainers"] = _format(gainers, "涨幅榜 (3%-9.5%)", "涨幅居前但未涨停，有追入空间")

    # 2. 放量上涨（量能异动）
    vol_break = df[(df["pct_chg"] > 2) & (df["pct_chg"] < 9)]
    vol_break = vol_break.nlargest(30, "amount")
    results["screens"]["volume_breakout"] = _format(vol_break, "成交额榜(涨)", "大资金关注，流动性好")

    # 3. 底部放量（超跌反弹信号）
    # 用当日涨幅>3% + 成交额>5亿作为底部放量 proxy
    bottom_reversal = df[
        (df["pct_chg"] > 2) & (df["pct_chg"] < 7) & (df["amount"] > 5e8)
    ].nlargest(20, "amount")
    results["screens"]["bottom_reversal"] = _format(bottom_reversal, "放量反弹", "涨幅温和放量，可能底部启动")

    # 4. 接近涨停（情绪指标）
    near_limit = df[df["pct_chg"] > 7].nlargest(20, "pct_chg")
    results["screens"]["near_limit"] = _format(near_limit, "强势拉升 (>7%)", "接近涨停，情绪高涨，注意追高风险")

    # 5. 高点突破候选（今日最高突破近5日大概率高点）
    # 用当日最高接近收盘价且涨幅>3%作为 proxy
    breakout = df[
        (df["pct_chg"] > 2) & (df["pct_chg"] < 8) &
        (df["high"] > 0) & (df["price"] / df["high"] > 0.95)  # 收盘接近最高价
    ].nlargest(20, "amount")
    results["screens"]["high_close"] = _format(breakout, "强势收盘 (光头阳线)", "收于日内高点附近，买方主导")

    # 6. 连续异动候选（需要历史数据，用当日强度 proxy）
    # 选涨幅3-7% + 成交额>3亿，这些大概率是强势启动
    strong = df[
        (df["pct_chg"] > 3) & (df["pct_chg"] < 7) & (df["amount"] > 3e8)
    ].nlargest(20, "pct_chg")
    results["screens"]["strong_start"] = _format(strong, "强势启动候选", "涨幅适中放量，值得跟踪")

    return results


def _format(df, title, desc):
    items = []
    for _, row in df.iterrows():
        items.append({
            "code": str(row["code"]),
            "name": str(row["name"]),
            "price": round(float(row["price"]), 2),
            "pct_chg": round(float(row["pct_chg"]), 2),
            "volume": int(row["volume"]),
            "amount": round(float(row["amount"]) / 1e8, 2),  # 亿
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
        })
    return {"title": title, "description": desc, "count": len(items), "stocks": items}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("正在拉取全市场行情 (新浪财经)...")
    df = fetch_all_stocks()
    logger.info("获取 %d 只股票，开始筛选...", len(df))
    results = screen(df)
    output_dir = Path("data/market")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "hot_stocks.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    logger.info("筛选结果已写入: %s", path)


if __name__ == "__main__":
    main()
