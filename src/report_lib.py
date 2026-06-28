"""共享报告函数库。被 orchestrator、HTML generator、monthly report 等 import。"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

_TZ_CN = timezone(timedelta(hours=8))
ROOT = Path(__file__).parent.parent

# ── Data loading ──────────────────────────────────────────────

def load_json(*parts):
    with open(ROOT.joinpath(*parts), encoding="utf-8") as f:
        return json.load(f)

def load_tracklist():
    return load_json("tracking", "tracklist.json")

def load_market_index():
    return load_json("data", "market", "index.json")

def load_sector_scan():
    p = ROOT / "data" / "market" / "sector_scan.json"
    if p.exists():
        return load_json("data", "market", "sector_scan.json")
    return None

def load_stock_data(code):
    """Return (indicators, quote, fundamentals) or (None,None,None)."""
    try:
        ind = load_json("data", code, "indicators.json")
        q = load_json("data", code, "quote.json")
        fund = load_json("data", code, "fundamentals.json")
        return ind, q, fund
    except Exception:
        return None, None, None

def load_all_stocks():
    """Return list of dicts with merged stock data."""
    tl = load_tracklist()
    result = []
    for s in tl["stocks"]:
        ind, q, fund = load_stock_data(s["code"])
        if not ind or not q:
            continue
        result.append({
            "code": s["code"], "name": s["name"], "tier": s["tier"],
            "has_position": s.get("has_position", False),
            "tags": s.get("tags", []),
            "price": q.get("price") or 0,
            "pct_chg": q.get("pct_chg") or 0,
            "turnover": q.get("turnover_rate") or 0,
            "trend": ind["trend"]["status"],
            "trend_strength": ind["trend"]["trend_strength"],
            "rsi6": ind["rsi"].get("rsi6") or 0,
            "rsi12": ind["rsi"].get("rsi12") or 0,
            "bias5": ind["bias"].get("bias5") or 0,
            "macd_hist": ind["macd"]["hist"],
            "ma5": ind["ma"]["ma5"], "ma10": ind["ma"]["ma10"], "ma20": ind["ma"]["ma20"],
            "pe": fund.get("pe"), "pb": fund.get("pb"),
            "mcap": fund.get("market_cap_yi"),
            "raw_indicators": ind, "raw_quote": q, "raw_fund": fund,
        })
    return result

def load_position(code, name):
    try:
        return load_json("tracking", f"{code}-{name}", "position.json")
    except Exception:
        return None

# ── PE / Valuation helpers ────────────────────────────────────

def pe_label(pe):
    if pe is None: return ("N/A", "#999")
    if pe < 0: return ("亏损", "#c0392b")
    if pe < 30: return ("低估", "#27ae60")
    if pe < 50: return ("合理", "#e67e22")
    if pe < 100: return ("偏高", "#e74c3c")
    return ("高估", "#c0392b")

def pe_bucket(pe):
    if pe is None: return "N/A"
    if pe < 0: return "亏损"
    if pe < 30: return "<30"
    if pe < 50: return "30-50"
    if pe < 100: return "50-100"
    if pe < 200: return "100-200"
    return ">200"

# ── Strategy helpers ──────────────────────────────────────────

def select_strategies(tier, trend_status):
    """Return list of (strategy_name, display_name) for a stock."""
    if trend_status in ("强势多头", "多头排列"):
        picks = [("bull_trend", "多头趋势"), ("volume_breakout", "放量突破")]
        if tier == "core":
            picks += [("ma_golden_cross", "均线金叉"), ("dragon_head", "龙头分析")]
        elif tier == "key":
            picks += [("ma_golden_cross", "均线金叉")]
    elif trend_status == "弱势多头":
        picks = [("bull_trend", "多头趋势"), ("shrink_pullback", "缩量回调")]
        if tier in ("core", "key"):
            picks += [("ma_golden_cross", "均线金叉")]
    elif trend_status in ("弱势空头", "空头排列"):
        picks = [("bottom_volume", "地量策略"), ("shrink_pullback", "缩量回调")]
        if tier == "core":
            picks += [("expectation_repricing", "预期重估"), ("emotion_cycle", "情绪周期")]
        elif tier == "key":
            picks += [("expectation_repricing", "预期重估")]
    else:
        picks = [("bull_trend", "趋势分析"), ("volume_breakout", "量价分析")]
    return picks

def simple_strategy(s):
    """Generate strategy signals for a stock dict. Returns list of signal dicts."""
    sigs = []
    rsi6 = s["rsi6"]; bias5 = s["bias5"]; ts = s["trend_strength"]
    macd_h = s["macd_hist"]; pct = s["pct_chg"]
    vr = s.get("vr", 1)  # volume ratio from fund or indicators

    # Trend signal
    if s["trend"] in ("强势多头", "多头排列"):
        if bias5 > 8 or rsi6 > 75:
            sigs.append({"name": "trend", "display": "趋势分析", "signal": "hold", "score": 55,
                         "reason": f"多头但RSI6={rsi6:.0f}超买/BIAS5={bias5:.1f}%偏高"})
        elif bias5 < 3:
            sigs.append({"name": "trend", "display": "趋势分析", "signal": "buy", "score": 68,
                         "reason": f"多头+价格贴近MA5({bias5:.1f}%)，好位置"})
        else:
            sigs.append({"name": "trend", "display": "趋势分析", "signal": "hold", "score": 60,
                         "reason": f"多头排列，RSI12={s['rsi12']:.0f}健康"})
    elif s["trend"] == "弱势多头":
        sigs.append({"name": "trend", "display": "趋势分析", "signal": "hold", "score": 48,
                     "reason": f"弱势多头(强度{ts})，等MA10上穿MA20"})
    else:
        if rsi6 < 30:
            sigs.append({"name": "trend", "display": "趋势分析", "signal": "hold", "score": 42,
                         "reason": f"空头但RSI6={rsi6:.0f}超卖"})
        else:
            sigs.append({"name": "trend", "display": "趋势分析", "signal": "sell", "score": 35,
                         "reason": f"空头排列(强度{ts})"})

    # Volume signal
    if vr > 2 and pct > 3:
        sigs.append({"name": "volume", "display": "量价分析", "signal": "buy", "score": 65,
                     "reason": f"量比{vr:.1f}放量上涨"})
    elif vr > 1.3 and pct > 0:
        sigs.append({"name": "volume", "display": "量价分析", "signal": "hold", "score": 55,
                     "reason": f"量比{vr:.1f}温和放量"})
    elif vr < 0.7 and pct < 0:
        sigs.append({"name": "volume", "display": "量价分析", "signal": "hold", "score": 48,
                     "reason": f"量比{vr:.1f}缩量下跌"})
    else:
        sigs.append({"name": "volume", "display": "量价分析", "signal": "hold", "score": 50,
                     "reason": f"量比{vr:.1f}正常"})

    # MACD signal
    if macd_h > 0.1:
        sigs.append({"name": "macd", "display": "MACD", "signal": "buy", "score": 62,
                     "reason": f"MACD红柱{macd_h:.2f}，多头"})
    elif macd_h > 0:
        sigs.append({"name": "macd", "display": "MACD", "signal": "hold", "score": 55,
                     "reason": f"MACD微红{macd_h:.2f}"})
    elif macd_h > -0.3:
        sigs.append({"name": "macd", "display": "MACD", "signal": "hold", "score": 45,
                     "reason": f"MACD绿柱{macd_h:.2f}，偏弱"})
    else:
        sigs.append({"name": "macd", "display": "MACD", "signal": "sell", "score": 35,
                     "reason": f"MACD死叉加深({macd_h:.2f})"})

    return sigs

# ── Date/Formatting helpers ───────────────────────────────────

_WEEKDAY = ["周一","周二","周三","周四","周五","周六","周日"]

def today_str():
    return datetime.now(_TZ_CN).strftime("%Y-%m-%d")

def date_cn(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year}年{dt.month}月{dt.day}日（{_WEEKDAY[dt.weekday()]}）"

def date_md_heading(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.month}月{dt.day}日（{_WEEKDAY[dt.weekday()]}）"

def fmt(v, f=".1f"):
    if v is None: return "N/A"
    try: return f"{{:{f}}}".format(v)
    except: return str(v)

# ── Consensus helpers ─────────────────────────────────────────

def consensus(signals):
    """Return (verdict, avg_score, buy_n, hold_n, sell_n)."""
    n = len(signals)
    if n == 0:
        return "无信号", 0, 0, 0, 0
    buy = sum(1 for s in signals if s["signal"] == "buy")
    hold = sum(1 for s in signals if s["signal"] == "hold")
    sell = sum(1 for s in signals if s["signal"] == "sell")
    avg = sum(s["score"] for s in signals) / n
    if avg >= 60: v = "偏多"
    elif avg >= 40: v = "中性"
    else: v = "偏空"
    return v, avg, buy, hold, sell
