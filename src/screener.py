#!/usr/bin/env python3
"""
全市场股票筛选器。基于新浪财经实时行情（通过 akshare）。
用法:
  python src/screener.py          # 仅 L1
  python src/screener.py --l2     # L1 + L2 技术指标评分
输出: data/market/screener.json, data/market/screener_l2.json
"""

import json
import logging
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
_TZ_CN = timezone(timedelta(hours=8))


# ============================================================
# L1: 单日快照筛选
# ============================================================

def fetch_all_stocks():
    import akshare as ak
    df = ak.stock_zh_a_spot()
    df = df.rename(columns={
        "代码": "code", "名称": "name",
        "最新价": "price", "涨跌额": "change", "涨跌幅": "pct_chg",
        "昨收": "prev_close", "今开": "open", "最高": "high", "最低": "low",
        "成交量": "volume", "成交额": "amount",
    })
    df = df[~df["code"].str.startswith(("8", "9"))]
    df = df[~df["name"].str.contains("ST|退|N|C", na=False)]
    for col in ["price", "pct_chg", "volume", "amount", "high", "low", "prev_close", "open"]:
        df[col] = df[col].astype(float)
    df["range_pct"] = (df["high"] - df["low"]) / df["prev_close"] * 100
    df["gap_pct"] = (df["open"] - df["prev_close"]) / df["prev_close"] * 100
    df["close_pos"] = (df["price"] - df["low"]) / (df["high"] - df["low"] + 0.001)
    return df


def screen_l1(df):
    r = {
        "updated_at": datetime.now(_TZ_CN).isoformat(),
        "total_stocks": len(df),
        "opportunity": {}, "oversold": {}, "anomaly": {},
    }
    # 机会
    r["opportunity"]["mild_breakout"] = _fmt(
        df[(df["pct_chg"] > 3) & (df["pct_chg"] < 7) & (df["amount"] > 3e8) & (df["close_pos"] > 0.4)].nlargest(25, "amount"),
        "温和放量上涨", "涨幅适中+成交活跃+收于中上部")
    r["opportunity"]["breakout"] = _fmt(
        df[(df["pct_chg"] > 2) & (df["pct_chg"] < 6) & (df["close_pos"] > 0.7)].nlargest(20, "amount"),
        "放量突破", "放量+收于日内高位")
    r["opportunity"]["gap_up"] = _fmt(
        df[(df["gap_pct"] > 1) & (df["low"] > df["prev_close"]) & (df["pct_chg"] < 5)].nlargest(15, "amount"),
        "跳空高开", "开盘跳空+日内未补缺口")
    # 超跌
    r["oversold"]["deep_cut"] = _fmt(
        df[(df["pct_chg"] < -5) & (df["pct_chg"] > -9.5) & (df["amount"] > 1e8)].nsmallest(25, "pct_chg"),
        "深度回调", "大跌5-9%未跌停")
    r["oversold"]["stablizing"] = _fmt(
        df[(df["pct_chg"] > -2) & (df["pct_chg"] < 0.5) & (df["range_pct"] < 3) & (df["amount"] > 0.5e8) & (df["amount"] < 10e8)].nlargest(20, "amount"),
        "缩量止跌", "振幅缩小+缩量")
    r["oversold"]["panic_sell"] = _fmt(
        df[(df["pct_chg"] < -3) & (df["pct_chg"] > -7) & (df["amount"] > 5e8)].nsmallest(20, "pct_chg"),
        "加速赶底", "放量下跌")
    # 异动
    r["anomaly"]["heavy_volume"] = _fmt(
        df[(df["range_pct"] > 5) & (df["amount"] > 10e8)].nlargest(20, "amount"),
        "巨量博弈", "高振幅+大成交")
    r["anomaly"]["doji"] = _fmt(
        df[(df["range_pct"] > 4) & (df["pct_chg"].abs() < 1.5) & (df["amount"] > 2e8)].nlargest(15, "amount"),
        "宽幅十字星", "变盘前兆")
    r["anomaly"]["top_amount"] = _fmt(df.nlargest(30, "amount"), "成交额TOP30", "大资金主战场")
    r["anomaly"]["wild_swing"] = _fmt(df[df["range_pct"] > 8].nlargest(20, "amount"), "极端振幅(>8%)", "异常波动")
    return r


def _fmt(df, title, desc):
    items = []
    for _, row in df.iterrows():
        items.append({
            "code": str(row["code"]), "name": str(row["name"]),
            "price": round(float(row["price"]), 2), "pct_chg": round(float(row["pct_chg"]), 2),
            "range_pct": round(float(row.get("range_pct", 0)), 2),
            "gap_pct": round(float(row.get("gap_pct", 0)), 2),
            "close_pos": round(float(row.get("close_pos", 0.5)), 2),
            "volume": int(row["volume"]), "amount": round(float(row["amount"]) / 1e8, 2),
        })
    return {"title": title, "description": desc, "count": len(items), "stocks": items}


def gather_l1_candidates(l1_result):
    """从 L1 结果中收集去重股票代码"""
    codes = set()
    for cat in ["opportunity", "oversold", "anomaly"]:
        for screen in l1_result[cat].values():
            for s in screen["stocks"]:
                codes.add(s["code"])
    logger.info("L1 去重候选: %d 只", len(codes))
    return list(codes)


# ============================================================
# L2: 技术指标评分
# ============================================================

def fetch_one(code):
    """对单只股票执行 fetch + indicators，返回 (code, success)"""
    try:
        venv = Path(sys.executable)
        project = Path(__file__).parent.parent
        fetch_py = project / "src" / "fetch.py"
        ind_py = project / "src" / "indicators.py"
        env = {"PATH": str(venv.parent), "VIRTUAL_ENV": str(venv.parent.parent / ".venv")}

        r1 = subprocess.run(
            [str(venv), str(fetch_py), "--code", code],
            capture_output=True, text=True, timeout=60,
            cwd=str(project), env={**__import__("os").environ, "PYTHONPATH": str(project)}
        )
        if r1.returncode != 0:
            return (code, False, f"fetch failed: {r1.stderr[-100:]}")

        r2 = subprocess.run(
            [str(venv), str(ind_py), "--code", code],
            capture_output=True, text=True, timeout=30,
            cwd=str(project), env={**__import__("os").environ, "PYTHONPATH": str(project)}
        )
        if r2.returncode != 0:
            return (code, False, f"indicators failed: {r2.stderr[-100:]}")

        return (code, True, None)
    except Exception as e:
        return (code, False, str(e)[:100])


def batch_fetch(codes, workers=8):
    """并行拉取 K 线 + 计算指标"""
    logger.info("L2 批量拉取 %d 只股票 (workers=%d)...", len(codes), workers)
    succeeded = []
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_one, c): c for c in codes}
        for i, f in enumerate(as_completed(futures)):
            code, ok, err = f.result()
            if ok:
                succeeded.append(code)
            else:
                failed.append((code, err))
            if (i + 1) % 20 == 0:
                logger.info("  进度: %d/%d (成功:%d 失败:%d)", i + 1, len(codes), len(succeeded), len(failed))
    logger.info("L2 拉取完成: 成功 %d, 失败 %d", len(succeeded), len(failed))
    if failed:
        logger.warning("失败详情: %s", failed[:5])
    return succeeded


def score_l2(code, store=None):
    """对单只股票执行技术指标评分，返回 (score, detail) 或 (None, None)"""
    from src.data_access import load_bars, load_indicators

    ind = load_indicators(code, store=store)
    kl = load_bars(code, store=store)
    if not ind or not kl.get("kline"):
        return None, None

    ma = ind.get("ma", {})
    macd = ind.get("macd", {})
    rsi = ind.get("rsi", {})
    vol = ind.get("volume", {})
    bias = ind.get("bias", {})
    trend = ind.get("trend", {})

    # 流动性底线
    avg_amount = vol.get("ma5_vol", 0) or 0
    # 估算: 量 × 均价
    kline_list = kl.get("kline", [])
    if kline_list and avg_amount:
        try:
            avg_price = sum(k.get("close", 0) for k in kline_list[-5:]) / 5
            daily_amount = avg_amount * avg_price
        except Exception:
            daily_amount = 0
    else:
        daily_amount = 0

    if daily_amount < 1e8:  # 日均 < 1亿
        return None, "流动性不足"
    if ma.get("ma5", 0) < 5:  # 股价 < 5元
        return None, "股价过低"

    score = 0
    details = []

    # ---- 趋势结构 (30分) ----
    ts = 0
    if ma.get("ma5", 0) > ma.get("ma10", 0) > ma.get("ma20", 0) > ma.get("ma60", 0):
        ts += 10; details.append("均线多头排列 +10")
    elif ma.get("ma5", 0) > ma.get("ma10", 0) > ma.get("ma20", 0):
        ts += 5; details.append("短期多头 +5")

    # MA60 方向 (近20日)
    if kline_list and len(kline_list) >= 20:
        recent = [k["close"] for k in kline_list[-20:]]
        ma60_20d = sum(recent) / len(recent)
        ma60_now = ma.get("ma60", 0)
        if ma60_now > ma60_20d * 1.01:
            ts += 5; details.append("MA60上行 +5")
        elif ma60_now > ma60_20d:
            ts += 3; details.append("MA60微升 +3")
        else:
            ts -= 5; details.append("MA60下行 -5")
    else:
        ts += 2; details.append("MA60趋势(数据不足) +2")

    # 价格 vs 60日高点
    if kline_list:
        high_60 = max(k["high"] for k in kline_list[-60:])
        pct_from_high = (ind.get("price", ind.get("quote_price", ma.get("ma5", 0))) - high_60) / high_60 * 100 if high_60 else 0
        if pct_from_high > -5:
            ts += 5; details.append("距60日高<5% +5")
        elif pct_from_high > -15:
            ts += 3; details.append("距60日高5-15% +3")
        else:
            ts += 0; details.append("距60日高>15% +0")

    # 价格 vs MA20
    pct_from_ma20 = (ind.get("price", ma.get("ma5", 0)) - ma.get("ma20", 0)) / ma.get("ma20", 1) * 100
    if pct_from_ma20 > 0:
        ts += 5; details.append("价格>MA20 +5")

    # MA 发散
    ma_gap = (ma.get("ma5", 0) - ma.get("ma20", 0)) / ma.get("ma20", 1) * 100
    if ma_gap > 5:
        ts += 5; details.append("均线发散 +5")
    elif ma_gap > 2:
        ts += 3; details.append("均线微发散 +3")

    score += max(0, ts)
    details.insert(0, f"趋势结构: {ts}/30")

    # ---- 量价形态 (25分) ----
    vp = 0
    if kline_list and len(kline_list) >= 20:
        high_20_close = max(k["close"] for k in kline_list[-21:-1])  # 昨日之前20日最高
        latest_close = kline_list[-1]["close"]
        if latest_close >= high_20_close:
            vp += 10; details.append("突破20日高 +10")

    vr = vol.get("volume_ratio", 0) or 0
    if vr >= 2.0:
        vp += 10; details.append("量比≥2 +10")
    elif vr >= 1.3:
        vp += 8; details.append("量比≥1.3 +8")
    elif vr >= 1.0:
        vp += 4; details.append("量比≥1 +4")

    if kline_list:
        last = kline_list[-1]
        if last.get("close", 0) > last.get("open", 0):
            vp += 5; details.append("阳线 +5")

    score += vp
    details.insert(1, f"量价形态: {vp}/25")

    # ---- MACD 动能 (20分) ----
    mc = 0
    dif = macd.get("dif", 0) or 0
    dea = macd.get("dea", 0) or 0
    hist = macd.get("hist", 0) or 0
    if dif > dea:
        mc += 10; details.append("MACD金叉 +10")
    if dif > 0:
        mc += 5; details.append("DIF>0 +5")
    if hist > 0 and kline_list and len(kline_list) >= 3:
        # 检查近3日红柱是否放大 (需要历史指标, 用当前kline倒推)
        mc += 5; details.append("红柱 +5")
    elif hist > 0:
        mc += 3; details.append("刚转红 +3")
    score += mc
    details.insert(2, f"MACD动能: {mc}/20")

    # ---- RSI 位置 (15分) ----
    rs = 0
    r6 = rsi.get("rsi6", 50) or 50
    r12 = rsi.get("rsi12", 50) or 50
    if 50 <= r6 <= 75:
        rs += 10; details.append(f"RSI6={r6:.0f} 强势 +10")
    elif 40 <= r6 < 50:
        rs += 6; details.append(f"RSI6={r6:.0f} 中性 +6")
    elif r6 < 30:
        rs += 0; details.append(f"RSI6={r6:.0f} 超卖(独立赛道) +0")
    elif r6 > 75:
        rs += 3; details.append(f"RSI6={r6:.0f} 超买 -7")
    if 45 <= r12 <= 70:
        rs += 5; details.append(f"RSI12={r12:.0f} 健康 +5")
    score += rs
    details.insert(3, f"RSI位置: {rs}/15")

    # ---- 乖离风控 (10分) ----
    br = 10
    b5 = bias.get("bias5", 0) or 0
    b20 = bias.get("bias20", 0) or 0
    if abs(b5) < 5:
        br -= 0
    elif abs(b5) < 8:
        br -= 3; details.append(f"BIAS5={b5:.1f}% 偏高 -3")
    else:
        br -= 5; details.append(f"BIAS5={b5:.1f}% 危险 -5")
    if abs(b20) < 15:
        br -= 0
    else:
        br -= 5; details.append(f"BIAS20={b20:.1f}% 过度偏离 -5")
    score += max(0, br)
    details.insert(4, f"乖离风控: {br}/10")

    # 组装
    detail_str = "; ".join(details[:8])
    name = kl.get("name", code)
    result = {
        "code": code, "name": name,
        "score": score,
        "trend_score": ts, "volume_score": vp, "macd_score": mc, "rsi_score": rs, "bias_score": br,
        "price": round(kline_list[-1]["close"], 2) if kline_list else 0,
        "pct_chg": round((kline_list[-1]["close"] / kline_list[-2]["close"] - 1) * 100, 2) if len(kline_list) >= 2 else 0,
        "ma5": ma.get("ma5"), "ma20": ma.get("ma20"),
        "volume_ratio": vr,
        "rsi6": r6, "bias5": b5,
        "detail": detail_str,
    }
    return score, result


def run_l2(l1_result):
    codes = gather_l1_candidates(l1_result)
    if not codes:
        logger.warning("L1 无候选，跳过 L2")
        return None

    succeeded = batch_fetch(codes, workers=8)

    logger.info("L2 评分中...")
    results = []
    for code in succeeded:
        score, detail = score_l2(code)
        if detail and isinstance(detail, dict):
            results.append(detail)
        elif detail:
            logger.debug("%s: %s", code, detail)

    results.sort(key=lambda x: -x["score"])

    strong = [r for r in results if r["score"] >= 70]
    watch = [r for r in results if 55 <= r["score"] < 70]
    weak = [r for r in results if r["score"] < 55]

    logger.info("L2 评分完成: 强推 %d, 可关注 %d, 淘汰 %d", len(strong), len(watch), len(weak))

    output = {
        "updated_at": datetime.now(_TZ_CN).isoformat(),
        "l1_candidates": len(codes),
        "l2_fetched": len(succeeded),
        "l2_scored": len(results),
        "threshold": 55,
        "strong": strong,     # ≥70
        "watch": watch,       # 55-69
        "weak": weak[:20],    # <55, 只保留top20供参考
    }
    return output


# ============================================================
# Main
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--l2", action="store_true", help="运行 L2 技术指标评分")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # L1
    t0 = time.time()
    logger.info("=== L1 全市场快照筛选 ===")
    df = fetch_all_stocks()
    l1 = screen_l1(df)
    output_dir = Path("data/market")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "screener.json", "w", encoding="utf-8") as f:
        json.dump(l1, f, ensure_ascii=False, indent=2, default=str)
    logger.info("L1 完成 (%.1fs): %d 只股票 → %d 维度的候选", time.time() - t0, l1["total_stocks"],
                sum(len(v["stocks"]) for cat in l1.values() if isinstance(cat, dict) for v in cat.values()))

    # L2
    if args.l2:
        logger.info("=== L2 技术指标评分 ===")
        l2 = run_l2(l1)
        if l2:
            with open(output_dir / "screener_l2.json", "w", encoding="utf-8") as f:
                json.dump(l2, f, ensure_ascii=False, indent=2, default=str)
            logger.info("L2 完成 (%.1fs): 强推 %d, 可关注 %d", time.time() - t0, len(l2["strong"]), len(l2["watch"]))
            # 打印强推
            if l2["strong"]:
                print("\n🏆 L2 强推 (≥70分):")
                for r in l2["strong"][:10]:
                    print(f"  {r['code']} {r['name']:6s}  {r['score']:2d}分  ¥{r['price']:.2f}  {r['detail']}")
            if l2["watch"]:
                print(f"\n📋 L2 可关注 (55-69分): {len(l2['watch'])} 只")
        logger.info("总耗时: %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
