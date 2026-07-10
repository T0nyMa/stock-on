#!/usr/bin/env python3
"""日报全量数据拉取：A股+港股+金价+指数+板块，一把跑完，不分步。
用法: python scripts/fetch_all_daily.py [--date YYYY-MM-DD]
输出: data/daily_snapshot.json (Claude 直接读这一个文件做分析)
"""
import json, logging, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
_TZ_CN = timezone(timedelta(hours=8))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_all")

# ── Stock definitions ──
A_STOCKS = [
    ("002050","三花智控"), ("603986","兆易创新"), ("300373","扬杰科技"),
    ("688012","中微公司"), ("002371","北方华创"), ("002164","宁波东力"),
    ("300100","双林股份"), ("002463","沪电股份"), ("000988","华工科技"),
    ("300308","中际旭创"), ("601138","工业富联"), ("002384","东山精密"),
    ("002428","云南锗业"), ("300408","三环集团"), ("600547","山东黄金"),
    ("600276","恒瑞医药"), ("600988","赤峰黄金"), ("603259","药明康德"),
    ("601899","紫金矿业"), ("600171","上海贝岭"), ("688795","摩尔线程"),
]
HK_STOCKS = [
    ("hk09988","阿里巴巴"), ("hk02050","三花智控"), ("hk01787","山东黄金"),
    ("hk03986","兆易创新"),
]

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0
    except:
        return False

def main():
    date_str = (sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--date'
                else datetime.now(_TZ_CN).strftime("%Y-%m-%d"))
    logger.info(f"=== 全量数据拉取: {date_str} ===")

    # Phase 1: Market + Gold + Sector (sequential, fast)
    logger.info("Phase 1: 指数+金价+板块")
    run(f"cd {ROOT} && source .venv/bin/activate && python src/fetch_market.py")
    run(f"cd {ROOT} && source .venv/bin/activate && python src/fetch_gold.py")
    run(f"cd {ROOT} && source .venv/bin/activate && python src/sector_scan.py", timeout=180)

    # Phase 2: A-shares in parallel (4 workers)
    logger.info("Phase 2: A股数据 (并行4线程)")
    def fetch_a(code, name):
        ok1 = run(f"cd {ROOT} && source .venv/bin/activate && python src/fetch.py --code {code}")
        ok2 = run(f"cd {ROOT} && source .venv/bin/activate && python src/indicators.py --code {code}")
        return code, name, ok1 and ok2

    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_a, c, n): c for c, n in A_STOCKS}
        for f in as_completed(futures):
            code, name, ok = f.result()
            results[code] = ok
            if not ok: logger.warning(f"A股 {name}({code}) 失败")

    ok_a = sum(results.values())
    logger.info(f"A股: {ok_a}/{len(A_STOCKS)}")

    # Phase 3: HK snapshot via QuoteProvider
    logger.info("Phase 3: 港股快照 (QuoteProvider)")
    try:
        from src.providers import QuoteProvider
        qp = QuoteProvider()
        hk_codes = [c for c, _ in HK_STOCKS]
        hk_snapshot = {}
        for hk_code, hk_name in HK_STOCKS:
            try:
                q = qp.get_realtime(hk_code)
                if q and q.price > 0:
                    hk_snapshot[hk_code] = {
                        "name": q.name or hk_name,
                        "price": q.price,
                        "prev_close": q.prev_close,
                        "open": q.open,
                        "high": q.high,
                        "low": q.low,
                        "pct_chg": q.change_pct,
                        "volume": q.volume,
                        "amount": q.amount,
                        "pe": q.pe,
                        "market_cap": q.market_cap,
                        "high_52w": q.high_52w,
                        "low_52w": q.low_52w,
                        "ytd": q.ytd,
                        "currency": "HKD",
                        "_evidence": {
                            "source": q.source,
                            "source_chain": q.source_chain,
                        },
                    }
            except Exception as e:
                logger.warning(f"港股快照 {hk_name}({hk_code}): {e}")
        hk_path = ROOT / "data" / "market" / "hk_snapshot.json"
        hk_path.parent.mkdir(parents=True, exist_ok=True)
        with open(hk_path, "w", encoding="utf-8") as f:
            json.dump(hk_snapshot, f, ensure_ascii=False, indent=2)
        logger.info(f"港股快照: {len(hk_snapshot)}只")
    except Exception as e:
        logger.warning(f"港股快照失败: {e}")

    # Phase 4: HK K-line + indicators via KlineProvider
    logger.info("Phase 4: 港股K线+指标 (KlineProvider)")
    hk_klines = {}
    hk_indicators = {}
    try:
        from src.providers import KlineProvider
        from src.stock_analyzer import StockTrendAnalyzer
        import pandas as pd
        kp = KlineProvider()
        analyzer = StockTrendAnalyzer()
        for code, name in HK_STOCKS:
            try:
                rows, evidence = kp.get_daily(code, limit=250)
                if not rows:
                    logger.warning(f"HK K-line {name}({code}): 无数据")
                    continue
                kline_records = [{
                    "date": r.date, "open": r.open, "close": r.close,
                    "high": r.high, "low": r.low, "volume": r.volume,
                } for r in rows]
                hk_klines[code] = {
                    "name": name,
                    "count": len(rows),
                    "kline": kline_records,
                }
                # Compute indicators for HK stock
                df = pd.DataFrame(kline_records)
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")
                result = analyzer.analyze(df, code)
                hk_indicators[code] = {
                    "name": name,
                    "ma5": round(result.ma5, 1) if result.ma5 else None,
                    "ma10": round(result.ma10, 1) if result.ma10 else None,
                    "ma20": round(result.ma20, 1) if result.ma20 else None,
                    "rsi6": round(result.rsi_6) if result.rsi_6 else None,
                    "rsi12": round(result.rsi_12) if result.rsi_12 else None,
                    "macd_hist": round(result.macd_bar, 2) if result.macd_bar else None,
                    "bias5": round(result.bias_ma5, 1) if result.bias_ma5 else None,
                    "trend": str(getattr(result.trend_status, "value", "") or result.trend_status),
                    "trend_strength": round(getattr(result, "trend_strength", 0), 1) if getattr(result, "trend_strength", 0) else 0,
                    "_evidence": evidence.to_dict(),
                }
            except Exception as e:
                logger.warning(f"HK K-line {name}({code}): {e}")
    except Exception as e:
        logger.warning(f"港股K线+指标失败: {e}")

    hk_kl_path = ROOT / "data" / "market" / "hk_klines.json"
    with open(hk_kl_path, "w", encoding="utf-8") as f:
        json.dump(hk_klines, f, ensure_ascii=False, indent=2)
    logger.info(f"港股K线: {len(hk_klines)}只, 指标: {len(hk_indicators)}只")

    # Phase 5: Build daily snapshot
    logger.info("Phase 5: 生成快照")
    from src.report_lib import load_all_stocks, load_market_index, load_sector_scan, simple_strategy, consensus, pe_label, fmt

    snapshot = {
        "date": date_str,
        "generated_at": datetime.now(_TZ_CN).isoformat(),
        "market": load_market_index(),
        "sector_top5": [],
        "gold": {},
        "hk_stocks": hk_snapshot,
        "hk_indicators": hk_indicators,
        "a_stocks": [],
    }

    # Sector top 5
    sector = load_sector_scan()
    if sector and sector.get("rankings"):
        for s in sector["rankings"][:5]:
            snapshot["sector_top5"].append({
                "name": s["name"], "score": s["score"],
                "avg_pct": s.get("avg_pct", 0), "up_ratio": s.get("up_ratio", 0)
            })

    # Gold
    try:
        with open(ROOT / "data" / "market" / "gold.json") as f:
            gold = json.load(f)
            snapshot["gold"] = {
                "comex": gold.get("comex", {}).get("最新价_美元每盎司"),
                "sge_spot": gold.get("sge", {}).get("现价_元每克"),
            }
    except: pass

    # A stocks with strategy signals
    stocks = load_all_stocks()
    for s in stocks:
        sigs = simple_strategy(s)
        v, avg, buy, hold, sell = consensus(sigs)
        snapshot["a_stocks"].append({
            "code": s["code"], "name": s["name"],
            "price": s["price"], "pct_chg": s["pct_chg"],
            "pe": s["pe"], "pb": s["pb"],
            "trend": s["trend"], "trend_strength": s["trend_strength"],
            "ma5": round(s["ma5"], 1), "ma10": round(s["ma10"], 1), "ma20": round(s["ma20"], 1),
            "rsi6": round(s["rsi6"]), "rsi12": round(s["rsi12"]),
            "macd_hist": round(s["macd_hist"], 2),
            "bias5": round(s["bias5"], 1),
            "turnover": s.get("turnover", 0),
            "consensus": v, "score": round(avg),
            "has_position": s.get("has_position", False),
            "tier": s["tier"],
        })

    out_path = ROOT / "data" / "daily_snapshot.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    logger.info("Phase 6: 量化分析产物")
    if not run(f"cd {ROOT} && source .venv/bin/activate && python scripts/run_quant_analysis.py --date {date_str}", timeout=300):
        logger.warning("量化分析失败；报告必须披露 data/report_context.json unavailable")

    logger.info(f"快照已生成: {out_path} ({len(snapshot['a_stocks'])}A股 + {len(snapshot.get('hk_stocks',{}))}港股)")
    logger.info("=== 全量数据拉取完成 ===")

if __name__ == "__main__":
    main()
