#!/usr/bin/env python3
"""Generate single-stock daily reports for all tracked stocks."""
import json, os, sys
from pathlib import Path

REPORT_DATE = "2026-06-24"
BASE = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, BASE)
from src.data_access import load_bars, load_fundamentals, load_indicators

# Market regime → strategy selection
STRATEGY_MAP = {
    "强势多头": {"priority": ["bull-trend", "volume-breakout", "ma-golden-cross"], "optional": ["dragon-head", "shrink-pullback", "hot-theme", "emotion-cycle"]},
    "弱势多头": {"priority": ["bull-trend", "shrink-pullback", "volume-breakout"], "optional": ["ma-golden-cross", "emotion-cycle"]},
    "空头排列": {"priority": ["expectation-repricing", "growth-quality", "bottom-volume", "emotion-cycle"], "optional": ["shrink-pullback"]},
    "震荡": {"priority": ["box-oscillation", "chan-theory", "wave-theory"], "optional": ["bottom-volume", "one-yang-three-yin"]},
}

def load_json(path):
    with open(path) as f:
        return json.load(f)

def load_all_stocks():
    tracklist = load_json(f"{BASE}/tracking/tracklist.json")
    stocks = []
    for s in tracklist["stocks"]:
        code = s["code"]
        try:
            kline = load_bars(code)
            fund = load_fundamentals(code) or {}
            ind = load_indicators(code) or {}
            last = kline["kline"][-1]
            stocks.append({
                "code": code, "name": s["name"], "tier": s["tier"],
                "tier_label": s["tier_label"], "has_position": s.get("has_position", False),
                "position_info": s.get("position_info"),
                "date": last["date"][:10],
                "open": last["open"], "high": last["high"], "low": last["low"],
                "close": last["close"], "pct_chg": last["pct_chg"],
                "volume_ratio": last.get("volume_ratio", "?"),
                "turnover": fund.get("turnover_rate", "?"),
                "pe": fund.get("pe"), "pb": fund.get("pb"),
                "market_cap": fund.get("market_cap"),
                "rsi6": ind["rsi"]["rsi6"], "rsi12": ind["rsi"]["rsi12"],
                "ma5": ind["ma"]["ma5"], "ma10": ind["ma"]["ma10"],
                "ma20": ind["ma"]["ma20"], "ma60": ind["ma"]["ma60"],
                "macd_dif": ind["macd"]["dif"], "macd_dea": ind["macd"]["dea"],
                "macd_hist": ind["macd"]["hist"],
                "bias5": ind["bias"]["bias5"],
                "trend": ind["trend"]["status"],
                "trend_strength": ind["trend"]["trend_strength"],
                "buy_signal": ind["buy_signal"]["signal"],
                "buy_score": ind["buy_signal"]["score"],
                "risk_factors": ind.get("risk_factors", []),
            })
        except Exception as e:
            print(f"ERROR loading {code}: {e}")
    return stocks

def select_strategies(tier, trend):
    mapping = STRATEGY_MAP.get(trend, STRATEGY_MAP["震荡"])
    if tier == "core":
        n_priority = 3
        n_optional = 1
    elif tier == "key":
        n_priority = 2
        n_optional = 1
    else:  # watch
        n_priority = 1
        n_optional = 1
    selected = mapping["priority"][:n_priority] + mapping["optional"][:n_optional]
    return selected[:n_priority + n_optional]

def simple_strategy(stock, strat_name):
    """Simplified strategy analysis based on indicators."""
    rsi = stock["rsi6"]
    macd_h = stock["macd_hist"]
    bias = stock["bias5"]
    vr = stock["volume_ratio"]
    trend = stock["trend"]
    price = stock["close"]
    ma5, ma10, ma20 = stock["ma5"], stock["ma10"], stock["ma20"]

    results = {
        "bull-trend": {
            "signal": "buy" if trend == "强势多头" and macd_h > 0 else ("hold" if trend == "弱势多头" else "sell"),
            "score": min(100, stock["trend_strength"] + (10 if macd_h > 0 else -10)),
            "reason": "强势多头，MACD零轴上" if macd_h > 0 and trend == "强势多头" else "趋势转弱，观望"
        },
        "volume-breakout": {
            "signal": "buy" if vr > 1.5 and stock["pct_chg"] > 2 else ("hold" if vr > 1.0 else "sell"),
            "score": min(90, 50 + int((vr - 0.8) * 40) + (10 if stock["pct_chg"] > 3 else 0)),
            "reason": f"量比{vr}，{'放量突破' if vr > 1.5 else '量能一般'}"
        },
        "ma-golden-cross": {
            "signal": "buy" if ma5 > ma10 and stock["macd_hist"] > 0 else ("hold" if ma5 > ma10 else "sell"),
            "score": 75 if (ma5 > ma10 > ma20) else (55 if ma5 > ma10 else 35),
            "reason": f"MA5({'上穿' if ma5 > ma10 else '下穿'})MA10" if abs(ma5 - ma10) < ma5 * 0.02 else f"MA5({ma5:.1f}) vs MA10({ma10:.1f})"
        },
        "shrink-pullback": {
            "signal": "buy" if vr < 0.8 and price > ma5 and macd_h > -0.5 else ("hold" if vr < 1.0 else "sell"),
            "score": 65 if vr < 0.7 else (50 if vr < 0.9 else 30),
            "reason": f"量比{vr}，{'缩量回踩健康' if vr < 0.8 else '量能正常，非缩量回踩'}"
        },
        "dragon-head": {
            "signal": "buy" if stock["pct_chg"] > 5 and vr > 1.2 else ("hold" if stock["pct_chg"] > 2 else "sell"),
            "score": 70 if stock["pct_chg"] > 5 else (50 if stock["pct_chg"] > 2 else 30),
            "reason": f"涨幅{stock['pct_chg']}%，{'领涨龙头' if stock['pct_chg'] > 5 else '跟随上涨'}"
        },
        "bottom-volume": {
            "signal": "buy" if vr < 0.5 and rsi < 35 else ("hold" if vr < 0.7 and rsi < 45 else "sell"),
            "score": 70 if (vr < 0.5 and rsi < 30) else (45 if vr < 0.7 else 25),
            "reason": f"量比{vr}/RSI6={rsi}，{'地量+超卖，底部信号' if vr < 0.5 and rsi < 35 else '非地量底部'}"
        },
        "emotion-cycle": {
            "signal": "buy" if rsi < 35 else ("hold" if 35 <= rsi <= 65 else "sell"),
            "score": 60 if rsi < 30 else (45 if rsi < 40 else 35),
            "reason": f"RSI6={rsi}，{'冰点区域' if rsi < 35 else ('中性' if rsi < 65 else '高潮退潮')}"
        },
        "expectation-repricing": {
            "signal": "buy" if stock["pe"] and stock["pe"] < 30 else ("hold" if stock["pe"] and stock["pe"] < 50 else "sell"),
            "score": 70 if stock["pe"] and stock["pe"] < 25 else (50 if stock["pe"] and stock["pe"] < 40 else 30),
            "reason": f"PE={stock['pe']}，{'低估值重估空间' if stock['pe'] and stock['pe'] < 30 else '估值偏高'}"
        },
        "growth-quality": {
            "signal": "buy" if stock["pe"] and stock["pe"] < 50 else ("hold" if stock["pe"] and stock["pe"] < 100 else "sell"),
            "score": 65 if stock["pe"] and stock["pe"] < 40 else (45 if stock["pe"] and stock["pe"] < 80 else 25),
            "reason": f"PE={stock['pe']}，{'估值合理偏高' if stock['pe'] and stock['pe'] > 80 else '基本面尚可'}"
        },
        "hot-theme": {
            "signal": "buy" if stock["pct_chg"] > 3 else ("hold" if stock["pct_chg"] > 0 else "sell"),
            "score": 65 if stock["pct_chg"] > 5 else (50 if stock["pct_chg"] > 0 else 30),
            "reason": f"涨幅{stock['pct_chg']}%，{'受益AI主线' if stock['pct_chg'] > 3 else '热点不明确'}"
        },
        "box-oscillation": {
            "signal": "hold",
            "score": 50,
            "reason": f"RSI={rsi}中性区间，震荡格局"
        },
        "chan-theory": {
            "signal": "hold",
            "score": 50,
            "reason": "震荡结构，无明确买卖点"
        },
        "wave-theory": {
            "signal": "hold",
            "score": 50,
            "reason": "波浪结构不明"
        },
        "one-yang-three-yin": {
            "signal": "buy" if stock["pct_chg"] > 3 and stock["open"] < stock["close"] else ("hold" if stock["pct_chg"] > 0 else "sell"),
            "score": 70 if stock["pct_chg"] > 5 else (50 if stock["pct_chg"] > 2 else 30),
            "reason": f"{'阳包阴形态' if stock['pct_chg'] > 3 else '非底部反转形态'}"
        },
        "event-driven": {
            "signal": "hold",
            "score": 50,
            "reason": "无重大事件驱动"
        },
    }
    return results.get(strat_name, {"signal": "hold", "score": 50, "reason": "待分析"})

def format_strategy_table(strategies):
    rows = []
    for s in strategies:
        rows.append(f"| `{s['name']}` | {s['type']} | **{s['signal']}** | {s['score']} | {s['reason']} |")
    return "\n".join(rows)

def gen_core_report(stock, strategies):
    pos = None
    pos_path = f"{BASE}/tracking/{stock['code']}-{stock['name']}/position.json"
    if os.path.exists(pos_path):
        pos = load_json(pos_path)

    # Strategy analysis
    strategy_results = []
    for sn in strategies:
        r = simple_strategy(stock, sn)
        r["name"] = sn
        type_map = {"bull-trend": "趋势", "volume-breakout": "量价", "ma-golden-cross": "趋势",
                    "shrink-pullback": "量价", "dragon-head": "龙头", "bottom-volume": "量价",
                    "emotion-cycle": "题材", "expectation-repricing": "基本面", "growth-quality": "基本面",
                    "hot-theme": "题材", "box-oscillation": "形态", "chan-theory": "形态",
                    "wave-theory": "形态", "one-yang-three-yin": "形态", "event-driven": "题材"}
        r["type"] = type_map.get(sn, "其他")
        strategy_results.append(r)

    # Consensus
    buys = sum(1 for r in strategy_results if r["signal"] == "buy")
    sells = sum(1 for r in strategy_results if r["signal"] == "sell")
    holds = sum(1 for r in strategy_results if r["signal"] == "hold")
    avg_score = sum(r["score"] for r in strategy_results) / len(strategy_results)

    # Valuation
    pe = stock["pe"]
    if pe and pe < 0:
        val = "亏损"
    elif pe and pe < 30:
        val = "偏低"
    elif pe and pe < 50:
        val = "合理"
    elif pe and pe < 100:
        val = "偏高"
    elif pe:
        val = "严重高估"
    else:
        val = "数据缺失"

    lines = []
    lines.append(f"# {stock['name']}（{stock['code']}）每日分析 — 2026年6月24日")
    lines.append("")
    lines.append("## 今日走势")
    lines.append(f"| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |")
    lines.append(f"|------|------|------|------|------|------|------|")
    lines.append(f"| {stock['open']} | {stock['high']} | {stock['low']} | {stock['close']} | {stock['pct_chg']:+.2f}% | {stock['volume_ratio']} | {stock['turnover']}% |")
    lines.append("")

    # Strategy consensus (3-5 strategies)
    lines.append(f"## 策略共识 ({len(strategy_results)}策略)")
    lines.append("| 策略 | 类型 | 信号 | 评分 | 依据 |")
    lines.append("|------|------|------|------|------|")
    lines.append(format_strategy_table(strategy_results))
    lines.append("")
    lines.append(f"**共识**: 买入{buys} | 持有{holds} | 卖出{sells} | 均分{avg_score:.0f}")
    lines.append("")

    # Fundamentals
    lines.append("## 基本面概览")
    lines.append("| PE | PB | 市值(亿) | RSI6 | 估值判断 |")
    lines.append("|------|------|------|------|------|")
    lines.append(f"| {pe or '?'} | {stock['pb'] or '?'} | {stock['market_cap'] or '?'} | {stock['rsi6']:.1f} | {val} |")
    pe_str = f"PE={pe}" if pe else ""
    bias_str = f"乖离MA5={stock['bias5']:.1f}%"
    if val == "亏损":
        lines.append(f"估值: PE为负(亏损)，PB={stock['pb']}，关注成长性而非PE估值。{bias_str}")
    elif pe and pe < 50:
        lines.append(f"估值偏低，PE={pe}在合理区间，结合增速PEG判断。{bias_str}")
    elif pe:
        lines.append(f"估值偏高，PE={pe}，需高增速支撑。{bias_str}")
    lines.append("")

    # Position strategy (if has position)
    if pos:
        p = pos["position"]
        lines.append("## 持仓策略")
        lines.append(f"- **成本**: {p['buy_price']} × {p['shares']}股 = ¥{p['cost']:,}")
        current_price = stock["close"]
        current_value = current_price * p["shares"]
        pnl = current_value - p["cost"]
        pnl_pct = (current_price / p["buy_price"] - 1) * 100
        lines.append(f"- **现价**: {current_price}，浮盈/浮亏 {pnl_pct:+.1f}%（¥{pnl:,.0f}）")
        if pos.get("key_levels", {}).get("stop_loss"):
            sl = pos["key_levels"]["stop_loss"]
            dist = (current_price / sl - 1) * 100
            lines.append(f"- **止损**: {sl}，距止损 {dist:+.1f}%")
        # Update position file
        p["current_price"] = current_price
        p["current_value"] = current_value
        p["unrealized_pnl"] = pnl
        p["unrealized_pnl_pct"] = round(pnl_pct, 1)

        # Check stop loss
        sl = pos.get("key_levels", {}).get("stop_loss", 0)
        if sl and current_price < sl:
            lines.append(f"- ⛔ **止损已触发**: 现价{current_price} < 止损{sl}")
        elif sl:
            lines.append(f"- ✅ 现价{current_price} > 止损{sl}，未触发")

        lines.append("")
        lines.append(f"### 今日操作建议")
        if pnl_pct < -15:
            lines.append(f"深度亏损{pnl_pct:.1f}%，不建议止损在地板价。关注反弹至MA10({stock['ma10']:.1f})附近减仓。")
        elif pnl_pct < -5:
            lines.append(f"浅度亏损{pnl_pct:.1f}%，若RSI反弹至50+可持有，否则减仓。")
        else:
            lines.append(f"盈利{pnl_pct:.1f}%，关注趋势变化，设移动止损。")
    else:
        lines.append("## 买入条件检查")
        if stock["trend"] == "强势多头":
            lines.append(f"- ✅ 趋势: 强势多头")
        elif stock["trend"] == "弱势多头":
            lines.append(f"- ⚠️ 趋势: 弱势多头，需等确认")
        else:
            lines.append(f"- ❌ 趋势: {stock['trend']}，不适合买入")
        lines.append(f"- 均线: MA5={stock['ma5']:.1f} MA10={stock['ma10']:.1f} MA20={stock['ma20']:.1f}")
        lines.append(f"- RSI6: {stock['rsi6']:.1f}")

    lines.append("")
    lines.append("## 关键价位")
    lines.append(f"| 阻力 | MA10 | MA5 | 现价 | MA20 | 支撑 |")
    lines.append(f"|------|------|-----|------|------|------|")
    ma60_support = f"MA60={stock['ma60']:.1f}" if stock['ma60'] else "?"
    lines.append(f"| — | {stock['ma10']:.1f} | {stock['ma5']:.1f} | **{stock['close']}** | {stock['ma20']:.1f} | {ma60_support} |")
    lines.append("")

    lines.append("## 操作建议")
    if stock["trend"] == "空头排列":
        if stock["rsi6"] < 30:
            lines.append(f"空头排列+RSI超卖({stock['rsi6']:.1f})，短期超跌反弹可能，但趋势未转，反弹即减仓机会。等待MA5上穿MA10确认趋势反转后再考虑做多。")
        else:
            lines.append(f"空头排列延续，RSI{stock['rsi6']:.1f}弱势。建议等待底部放量反弹信号出现后再操作。暂不加仓。")
    elif stock["trend"] == "强势多头":
        if stock["rsi6"] > 75:
            lines.append(f"强势多头但RSI超买({stock['rsi6']:.1f})，乖离率{stock['bias5']:.1f}%，短期追高风险大。建议等缩量回踩MA5/MA10再考虑加仓。")
        else:
            lines.append(f"强势多头趋势，可沿MA5/MA10低吸。止损设在MA20({stock['ma20']:.1f})下方。")
    else:
        lines.append(f"{stock['trend']}格局，谨慎操作。关注量能变化和均线支撑。")

    return "\n".join(lines)

def gen_key_report(stock, strategies):
    strategy_results = []
    for sn in strategies:
        r = simple_strategy(stock, sn)
        r["name"] = sn
        type_map = {"bull-trend": "趋势", "volume-breakout": "量价", "ma-golden-cross": "趋势",
                    "shrink-pullback": "量价", "dragon-head": "龙头", "bottom-volume": "量价",
                    "emotion-cycle": "题材", "expectation-repricing": "基本面", "growth-quality": "基本面",
                    "hot-theme": "题材", "box-oscillation": "形态"}
        r["type"] = type_map.get(sn, "其他")
        strategy_results.append(r)

    pe = stock["pe"]
    if pe and pe < 0: val = "亏损"
    elif pe and pe < 30: val = "偏低"
    elif pe and pe < 50: val = "合理"
    elif pe and pe < 100: val = "偏高"
    elif pe: val = "严重高估"
    else: val = "数据缺失"

    lines = []
    lines.append(f"# {stock['name']}（{stock['code']}）每日分析 — 2026年6月24日")
    lines.append("")
    lines.append("## 今日走势")
    lines.append(f"| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |")
    lines.append(f"|------|------|------|------|------|------|------|")
    lines.append(f"| {stock['open']} | {stock['high']} | {stock['low']} | {stock['close']} | {stock['pct_chg']:+.2f}% | {stock['volume_ratio']} | {stock['turnover']}% |")
    lines.append("")

    lines.append(f"## 策略信号 ({len(strategy_results)}策略)")
    lines.append("| 策略 | 类型 | 信号 | 评分 | 依据 |")
    lines.append("|------|------|------|------|------|")
    lines.append(format_strategy_table(strategy_results))
    lines.append("")

    lines.append("## 基本面概览")
    lines.append("| PE | PB | 市值(亿) | RSI6 | 估值判断 |")
    lines.append("|------|------|------|------|------|")
    lines.append(f"| {pe or '?'} | {stock['pb'] or '?'} | {stock['market_cap'] or '?'} | {stock['rsi6']:.1f} | {val} |")
    pe_str = ""
    if pe and pe < 50:
        pe_str = f"估值偏低，PE={pe}在合理区间。"
    elif pe:
        pe_str = f"估值偏高，PE={pe}，需高增速支撑。"
    lines.append(pe_str)
    lines.append("")

    # Position (if any)
    pos_path = f"{BASE}/tracking/{stock['code']}-{stock['name']}/position.json"
    has_position = False
    if os.path.exists(pos_path):
        pos = load_json(pos_path)
        if "position" in pos:
            has_position = True
            p = pos["position"]
            cp = stock["close"]
            cv = cp * p["shares"]
            pnl = cv - p["cost"]
            pnl_pct = (cp / p["buy_price"] - 1) * 100
            p["current_price"] = cp
            p["current_value"] = cv
            p["unrealized_pnl"] = pnl
            p["unrealized_pnl_pct"] = round(pnl_pct, 1)
            lines.append("## 持仓策略")
            lines.append(f"- **成本**: {p['buy_price']} × {p['shares']}股 = ¥{p['cost']:,}")
            lines.append(f"- **现价**: {cp}，浮盈/浮亏 {pnl_pct:+.1f}%（¥{pnl:,.0f}）")
            if pos.get("key_levels", {}).get("stop_loss"):
                sl = pos["key_levels"]["stop_loss"]
                dist = (cp / sl - 1) * 100
                lines.append(f"- **止损**: {sl}，距止损 {dist:+.1f}%")
            # Check scenarios
            sp = pos.get("swing_plan", {})
            if sp.get("scenario_c", {}).get("status") == "triggered":
                lines.append(f"\n⛔ 昨日减仓触发条件已满足，今日开盘应执行减仓操作。")
            lines.append("")
            lines.append("### 操作指令")
            lines.append(f"具体操作请参考昨日plan。当前价格{cp}。")
            # Write updated position
            pos["last_updated"] = f"{REPORT_DATE}T18:00:00+08:00"
            with open(pos_path, 'w') as f:
                json.dump(pos, f, ensure_ascii=False, indent=2)
    if not has_position:
        lines.append("## 买入条件检查")
        if stock["trend"] in ("强势多头", "弱势多头"):
            lines.append(f"- ✅ 趋势: {stock['trend']}")
        else:
            lines.append(f"- ❌ 趋势: {stock['trend']}")
        lines.append(f"- RSI6: {stock['rsi6']:.1f}")

    lines.append("")
    lines.append("## 操作建议")
    if stock["trend"] == "强势多头":
        if stock["rsi6"] > 75:
            lines.append(f"强势多头但RSI超买({stock['rsi6']:.1f})，乖离{stock['bias5']:.1f}%偏高，短期不宜追高。等回踩MA5({stock['ma5']:.1f})附近再考虑。")
        else:
            lines.append(f"强势多头趋势良好，沿MA5({stock['ma5']:.1f})低吸。")
    elif stock["trend"] == "弱势多头":
        lines.append(f"弱势多头，关注MA20({stock['ma20']:.1f})支撑，若跌破则转空。暂观望。")
    else:
        lines.append(f"{stock['trend']}，不建议操作。")

    return "\n".join(lines)

def gen_watch_report(stock, strategies):
    strategy_results = []
    for sn in strategies:
        r = simple_strategy(stock, sn)
        r["name"] = sn
        type_map = {"bull-trend": "趋势", "volume-breakout": "量价", "ma-golden-cross": "趋势",
                    "shrink-pullback": "量价", "dragon-head": "龙头", "bottom-volume": "量价",
                    "emotion-cycle": "题材", "expectation-repricing": "基本面", "growth-quality": "基本面",
                    "hot-theme": "题材", "box-oscillation": "形态", "chan-theory": "形态"}
        r["type"] = type_map.get(sn, "其他")
        strategy_results.append(r)

    pe = stock["pe"]
    if pe and pe < 0: val = "亏损"
    elif pe and pe < 30: val = "偏低"
    elif pe and pe < 50: val = "合理"
    elif pe and pe < 100: val = "偏高"
    elif pe: val = "严重高估"
    else: val = "数据缺失"

    lines = []
    lines.append(f"# {stock['name']}（{stock['code']}）每日分析 — 2026年6月24日")
    lines.append("")
    lines.append("## 今日走势")
    lines.append(f"| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |")
    lines.append(f"|------|------|------|------|------|------|------|")
    lines.append(f"| {stock['open']} | {stock['high']} | {stock['low']} | {stock['close']} | {stock['pct_chg']:+.2f}% | {stock['volume_ratio']} | {stock['turnover']}% |")
    lines.append("")

    lines.append(f"## 策略信号 ({len(strategy_results)}策略)")
    lines.append("| 策略 | 类型 | 信号 | 评分 | 依据 |")
    lines.append("|------|------|------|------|------|")
    lines.append(format_strategy_table(strategy_results))
    lines.append("")

    lines.append("## 基本面速览")
    lines.append("| PE | PB | 市值(亿) | RSI6 | 状态 |")
    lines.append("|------|------|------|------|------|")
    lines.append(f"| {pe or '?'} | {stock['pb'] or '?'} | {stock['market_cap'] or '?'} | {stock['rsi6']:.1f} | {val} |")
    lines.append("")

    lines.append("## 操作建议")
    if stock["trend"] == "强势多头":
        if stock["rsi6"] > 80:
            lines.append(f"极度超买，RSI6={stock['rsi6']:.1f}，短调风险大，观望。")
        else:
            lines.append(f"趋势良好，可关注。{stock['trend']}，RSI={stock['rsi6']:.1f}")
    elif stock["trend"] == "空头排列":
        lines.append(f"空头排列，不建议参与。等待反转信号。")
    else:
        lines.append(f"{stock['trend']}，{stock['buy_signal']}({stock['buy_score']})。")

    return "\n".join(lines)

if __name__ == "__main__":
    stocks = load_all_stocks()
    print(f"Loaded {len(stocks)} stocks")

    for stock in stocks:
        strategies = select_strategies(stock["tier"], stock["trend"])
        print(f"\n{stock['tier_label']} {stock['name']}({stock['code']}): trend={stock['trend']}, strategies={strategies}")

        if stock["tier"] == "core":
            report = gen_core_report(stock, strategies)
        elif stock["tier"] == "key":
            report = gen_key_report(stock, strategies)
        else:
            report = gen_watch_report(stock, strategies)

        out_path = f"{BASE}/tracking/{stock['code']}-{stock['name']}/{REPORT_DATE}-analysis.md"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            f.write(report)
        print(f"  → {out_path}")

    print("\nAll reports generated!")
