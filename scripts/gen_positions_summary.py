#!/usr/bin/env python3
"""Generate position observation summary for 2026-06-24."""
import json, os, math, sys
from pathlib import Path

REPORT_DATE = "2026-06-24"
BASE = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, BASE)
from src.data_access import load_bars, load_fundamentals, load_indicators

def load_json(path):
    with open(path) as f:
        return json.load(f)

def load_all_stocks():
    tracklist = load_json(f"{BASE}/tracking/tracklist.json")
    stocks = []
    for s in tracklist["stocks"]:
        code = s["code"]
        try:
            fund = load_fundamentals(code) or {}
            ind = load_indicators(code) or {}
            kline = load_bars(code)
            last = kline["kline"][-1]
            pos_path = f"{BASE}/tracking/{code}-{s['name']}/position.json"
            pos = load_json(pos_path) if os.path.exists(pos_path) else None
            has_position = pos and "position" in pos and s.get("has_position")

            stock = {
                "code": code, "name": s["name"], "tier": s["tier"],
                "tier_label": s["tier_label"], "has_position": has_position,
                "close": last["close"], "pct_chg": last["pct_chg"],
                "volume_ratio": last.get("volume_ratio", "?"),
                "turnover": fund.get("turnover_rate", "?"),
                "rsi6": ind["rsi"]["rsi6"],
                "pe": fund.get("pe"), "pb": fund.get("pb"),
                "market_cap": fund.get("market_cap"),
                "trend": ind["trend"]["status"],
                "buy_signal": ind["buy_signal"]["signal"],
                "buy_score": ind["buy_signal"]["score"],
            }
            if pos and "position" in pos:
                p = pos["position"]
                stock["pnl_pct"] = (stock["close"] / p["buy_price"] - 1) * 100
                stock["buy_price"] = p["buy_price"]
                stock["shares"] = p["shares"]
                stock["cost"] = p["cost"]
                stock["pnl_amount"] = stock["close"] * p["shares"] - p["cost"]
            stocks.append(stock)
        except Exception as e:
            print(f"ERROR loading {code}: {e}")
    return stocks

def pe_bucket(pe):
    if pe is None: return "?"
    if pe < 0: return "亏损"
    if pe < 30: return "<30"
    if pe < 50: return "30-50"
    if pe < 100: return "50-100"
    if pe < 200: return "100-200"
    return ">200"

stocks = load_all_stocks()

# Sort by tier
tier_order = {"core": 0, "key": 1, "watch": 2}
stocks.sort(key=lambda s: (tier_order.get(s["tier"], 9), s["code"]))

lines = []
lines.append(f"# 持仓观察汇总 — 2026年6月24日")
lines.append("")

# === Core Positions ===
core_stocks = [s for s in stocks if s["tier"] == "core"]
key_stocks = [s for s in stocks if s["tier"] == "key"]
watch_stocks = [s for s in stocks if s["tier"] == "watch"]

lines.append("## ★ 核心持仓")
lines.append("")

for s in core_stocks:
    pos = load_json(f"{BASE}/tracking/{s['code']}-{s['name']}/position.json") if os.path.exists(f"{BASE}/tracking/{s['code']}-{s['name']}/position.json") else None
    lines.append(f"### {s['name']}（{s['code']}）— {s['tier_label']}")
    lines.append("")
    lines.append(f"**今日**: 收盘{s['close']}，{s['pct_chg']:+.2f}%，量比{s['volume_ratio']}，换手{s['turnover']}%")
    lines.append("")
    if s.get("pnl_pct") is not None:
        lines.append(f"**持仓**: 成本{s['buy_price']} × {s['shares']}股，浮亏{s['pnl_pct']:.1f}%（¥{s['pnl_amount']:,.0f}）")
        sl = pos.get("key_levels", {}).get("stop_loss", "?") if pos else "?"
        lines.append(f"**止损**: {sl}，MA5={s.get('ma5', '?')}，MA10={s.get('ma10', '?')}")
    lines.append(f"**策略信号**: {s['trend']}，RSI6={s['rsi6']:.1f}")
    # Read today's analysis for strategy consensus
    analysis_path = f"{BASE}/tracking/{s['code']}-{s['name']}/{REPORT_DATE}-analysis.md"
    if os.path.exists(analysis_path):
        with open(analysis_path) as f:
            content = f.read()
        for line in content.split("\n"):
            if "共识" in line and "买入" in line:
                lines.append(f"**{line.strip()}**")
                break
    lines.append(f"**建议**: PE={s['pe']}，PB={s['pb']}，估值合理。空头排列延续，RSI={s['rsi6']:.1f}弱势，暂不加仓，等待底部放量反转信号。")
    lines.append("")
    lines.append("---")
    lines.append("")

# === Key Observation ===
lines.append("## ★ 重点观察")
lines.append("")

for s in key_stocks:
    pos = load_json(f"{BASE}/tracking/{s['code']}-{s['name']}/position.json") if os.path.exists(f"{BASE}/tracking/{s['code']}-{s['name']}/position.json") else None
    lines.append(f"### {s['name']}（{s['code']}）")
    lines.append(f"收盘{s['close']}（{s['pct_chg']:+.2f}%）| 量比{s['volume_ratio']} | RSI6={s['rsi6']:.1f} | PE={s['pe']} | 趋势: {s['trend']}")
    lines.append(f"策略: {s['buy_signal']}({s['buy_score']})")
    if s.get("pnl_pct") is not None:
        lines.append(f"持仓: 成本{s['buy_price']}，{s['shares']}股，浮亏{s['pnl_pct']:.1f}%（¥{s['pnl_amount']:,.0f}）")
        if pos:
            sp = pos.get("swing_plan", {})
            if sp.get("scenario_c", {}).get("status") == "triggered":
                lines.append(f"⛔ 减仓触发！今日应执行减仓操作")
    lines.append("")

# === General Observation ===
lines.append("## 一般观察")
lines.append("")
lines.append("| 股票 | 收盘 | 涨跌 | 量比 | RSI6 | PE | PB | 市值(亿) | 趋势 | 信号 |")
lines.append("|------|------|------|------|------|----|----|---------|------|------|")

for s in watch_stocks:
    pe = f"{s['pe']:.0f}" if s['pe'] and s['pe'] > 0 else ("亏损" if s['pe'] and s['pe'] < 0 else "?")
    pb = f"{s['pb']:.1f}" if s['pb'] else "?"
    mc = f"{s['market_cap']:.0f}" if s['market_cap'] else "?"
    lines.append(f"| {s['name']}({s['code']}) | {s['close']} | {s['pct_chg']:+.2f}% | {s['volume_ratio']} | {s['rsi6']:.1f} | {pe} | {pb} | {mc} | {s['trend']} | {s['buy_signal']}({s['buy_score']}) |")

lines.append("")
lines.append("## 基本面估值分布")
lines.append("")

# PE distribution
buckets = {}
for s in stocks:
    b = pe_bucket(s["pe"])
    buckets[b] = buckets.get(b, 0) + 1

lines.append("| PE区间 | 数量 | 股票 |")
lines.append("|--------|------|------|")
for b in ["<30", "30-50", "50-100", "100-200", ">200", "亏损", "?"]:
    if b in buckets:
        names = [s["name"] for s in stocks if pe_bucket(s["pe"]) == b]
        names_str = "、".join(names)
        lines.append(f"| {b} | {buckets[b]} | {names_str} |")

lines.append("")
lines.append("### 估值洼地（PE<50）")
undervalued = [s for s in stocks if s["pe"] and s["pe"] > 0 and s["pe"] < 50]
if undervalued:
    for s in undervalued:
        lines.append(f"- **{s['name']}**({s['code']}): PE={s['pe']:.0f}，PB={s['pb']:.1f}，{s['tier_label']}")
        lines.append(f"  收盘{s['close']}，{s['trend']}，{'配置价值突出' if s['pe'] < 30 else '估值合理可关注'}")
else:
    lines.append("- 无PE<50标的")

lines.append("")
lines.append("### 高估预警（PE>100 或 亏损）")
overvalued = [s for s in stocks if (s["pe"] and (s["pe"] > 100 or s["pe"] < 0))]
if overvalued:
    for s in overvalued:
        label = f"PE={s['pe']:.0f}" if s['pe'] > 100 else "亏损"
        lines.append(f"- {s['name']}({s['code']}): {label}，{s['tier_label']}，高估值需业绩兑现")
else:
    lines.append("- 无极端高估值标的")

lines.append("")
lines.append("---")
lines.append(f"*报告生成时间: 2026-06-24 18:00 CST*")

out_path = f"{BASE}/tracking/daily/positions/{REPORT_DATE}.md"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w') as f:
    f.write("\n".join(lines))
print(f"Written: {out_path}")
print("Done!")
