#!/usr/bin/env python3
"""
全市场股票筛选器。基于新浪财经实时行情（通过 akshare）。
用法: python src/screener.py
输出: data/market/screener.json

三类信号:
  机会(看涨) — 强势启动、放量突破、光头阳线
  超跌(抄底) — 大跌企稳、缩量止跌、恐慌抛售
  异动(关注) — 巨量换手、宽幅震荡、高成交额
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
_TZ_CN = timezone(timedelta(hours=8))


def fetch_all_stocks():
    import akshare as ak
    df = ak.stock_zh_a_spot()
    df = df.rename(columns={
        "代码": "code", "名称": "name",
        "最新价": "price", "涨跌额": "change", "涨跌幅": "pct_chg",
        "昨收": "prev_close", "今开": "open", "最高": "high", "最低": "low",
        "成交量": "volume", "成交额": "amount",
    })
    # 排除北交所(8)、新三板(9)、ST、新股
    df = df[~df["code"].str.startswith(("8", "9"))]
    df = df[~df["name"].str.contains("ST|退|N|C", na=False)]
    for col in ["price", "pct_chg", "volume", "amount", "high", "low", "prev_close", "open"]:
        df[col] = df[col].astype(float)
    # 计算衍生指标
    df["range_pct"] = (df["high"] - df["low"]) / df["prev_close"] * 100  # 振幅
    df["gap_pct"] = (df["open"] - df["prev_close"]) / df["prev_close"] * 100  # 跳空
    df["close_pos"] = (df["price"] - df["low"]) / (df["high"] - df["low"] + 0.001)  # 收盘在日内位置(0-1)
    return df


def screen(df):
    r = {
        "updated_at": datetime.now(_TZ_CN).isoformat(),
        "total_stocks": len(df),
        "opportunity": {},   # 看涨机会
        "oversold": {},      # 超跌抄底
        "anomaly": {},       # 异动关注
    }

    # ========== 机会信号 ==========

    # 1. 温和放量上涨 (涨幅3-7% + 成交额>3亿) — 最值得跟踪
    mild_up = df[(df["pct_chg"] > 3) & (df["pct_chg"] < 7) & (df["amount"] > 3e8) & (df["close_pos"] > 0.4)]
    mild_up = mild_up.nlargest(25, "amount")
    r["opportunity"]["mild_breakout"] = _fmt(mild_up, "温和放量上涨", "涨幅适中+成交活跃+收于中上部，最值得跟踪的启动信号")

    # 2. 放量突破 (涨幅2-6% + top成交额 + 光头阳线)
    breakout = df[(df["pct_chg"] > 2) & (df["pct_chg"] < 6) & (df["close_pos"] > 0.7)]
    breakout = breakout.nlargest(20, "amount")
    r["opportunity"]["breakout"] = _fmt(breakout, "放量突破", "放量+收于日内高位，买方主导的突破信号")

    # 3. 跳空高开未补缺口 (开盘>昨收 + 最低>昨收 + 涨幅<5%)
    gap_up = df[(df["gap_pct"] > 1) & (df["low"] > df["prev_close"]) & (df["pct_chg"] < 5)]
    gap_up = gap_up.nlargest(15, "amount")
    r["opportunity"]["gap_up"] = _fmt(gap_up, "跳空高开", "开盘跳空+日内未补缺口，强势信号")

    # ========== 超跌信号 ==========

    # 4. 跌幅榜 (跌5-9% + 成交额>1亿) — 恐慌下跌，可能超卖反弹
    losers = df[(df["pct_chg"] < -5) & (df["pct_chg"] > -9.5) & (df["amount"] > 1e8)]
    losers = losers.nsmallest(25, "pct_chg")  # 跌幅最深
    r["oversold"]["deep_cut"] = _fmt(losers, "深度回调", "大跌5-9%但未跌停，恐慌抛售后的超卖反弹机会")

    # 5. 缩量止跌 (跌幅0-2% + 振幅<3% + 成交额>0.5亿) — 企稳信号
    stablizing = df[
        (df["pct_chg"] > -2) & (df["pct_chg"] < 0.5) &
        (df["range_pct"] < 3) & (df["amount"] > 0.5e8) & (df["amount"] < 10e8)
    ]
    stablizing = stablizing.nlargest(20, "amount")
    r["oversold"]["stablizing"] = _fmt(stablizing, "缩量止跌", "跌幅收窄+振幅缩小，可能接近阶段性底部")

    # 6. 恐慌抛售 (跌3-7% + 放量 >5亿) — 加速赶底
    panic = df[(df["pct_chg"] < -3) & (df["pct_chg"] > -7) & (df["amount"] > 5e8)]
    panic = panic.nsmallest(20, "pct_chg")
    r["oversold"]["panic_sell"] = _fmt(panic, "加速赶底", "放量下跌中，恐慌盘出清后的反弹机会（需等止跌确认）")

    # ========== 异动信号 ==========

    # 7. 巨量换手 (振幅>5% + 成交额>10亿) — 资金博弈激烈
    volatile = df[(df["range_pct"] > 5) & (df["amount"] > 10e8)]
    volatile = volatile.nlargest(20, "amount")
    r["anomaly"]["heavy_volume"] = _fmt(volatile, "巨量博弈", "高振幅+大成交额，多空激烈对抗，方向即将明朗")

    # 8. 宽幅震荡收十字星 (振幅>4% + 涨跌<1.5%) — 变盘前兆
    doji = df[(df["range_pct"] > 4) & (df["pct_chg"].abs() < 1.5) & (df["amount"] > 2e8)]
    doji = doji.nlargest(15, "amount")
    r["anomaly"]["doji"] = _fmt(doji, "宽幅十字星", "高振幅但收平，多空平衡，即将变盘")

    # 9. 高成交额榜 (全市场 top 30) — 主流资金主战场
    top_amount = df.nlargest(30, "amount")
    r["anomaly"]["top_amount"] = _fmt(top_amount, "全市场成交额TOP30", "大资金主战场，市场主线所在")

    # 10. 振幅极端 (振幅>8%) — 异常波动
    wild = df[df["range_pct"] > 8].nlargest(20, "amount")
    r["anomaly"]["wild_swing"] = _fmt(wild, "极端振幅 (>8%)", "日内巨幅波动，风险与机会并存")

    return r


def _fmt(df, title, desc):
    items = []
    for _, row in df.iterrows():
        items.append({
            "code": str(row["code"]),
            "name": str(row["name"]),
            "price": round(float(row["price"]), 2),
            "pct_chg": round(float(row["pct_chg"]), 2),
            "range_pct": round(float(row.get("range_pct", 0)), 2),
            "gap_pct": round(float(row.get("gap_pct", 0)), 2),
            "close_pos": round(float(row.get("close_pos", 0.5)), 2),
            "volume": int(row["volume"]),
            "amount": round(float(row["amount"]) / 1e8, 2),
        })
    return {"title": title, "description": desc, "count": len(items), "stocks": items}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger.info("正在拉取全市场行情...")
    df = fetch_all_stocks()
    logger.info("获取 %d 只股票，开始筛选...", len(df))
    results = screen(df)
    output_dir = Path("data/market")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "screener.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # 汇总
    for cat, screens in [("机会", results["opportunity"]), ("超跌", results["oversold"]), ("异动", results["anomaly"])]:
        total = sum(v["count"] for v in screens.values())
        logger.info("%s: %d 只 (%s)", cat, total, ", ".join(screens.keys()))
    logger.info("结果已写入: %s", path)


if __name__ == "__main__":
    main()
