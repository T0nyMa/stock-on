#!/usr/bin/env python3
"""日报全流程编排脚本。可被 cron 直接调用，不依赖 Claude。
用法: python scripts/orchestrate_daily.py [--date YYYY-MM-DD] [--skip-fetch] [--dry-run]
"""
import argparse, json, logging, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
_TZ_CN = timezone(timedelta(hours=8))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("orchestrate")

# ── Step 0: Validate ──────────────────────────────────────────

def validate_data(date_str):
    """Return True if data is fresh enough."""
    errors = []
    try:
        idx = json.load(open(ROOT / "data/market/index.json"))
        data_date = idx.get("_data_date", "")
        logger.info("Phase 0: market data date=%s, expected=%s", data_date, date_str)
        if data_date != date_str:
            errors.append(f"Market data date {data_date} != {date_str}")
    except Exception as e:
        errors.append(f"Cannot read market index: {e}")

    # Spot-check fundamentals
    for code in ["002050", "601138"]:
        try:
            fund = json.load(open(ROOT / "data" / code / "fundamentals.json"))
            if fund.get("pe") is None or fund.get("pb") is None:
                errors.append(f"{code} PE/PB is null")
        except Exception as e:
            errors.append(f"{code} fundamentals: {e}")

    if errors:
        logger.warning("Phase 0 FAILED: %s", "; ".join(errors))
        return False
    logger.info("Phase 0 PASSED")
    return True

# ── Step 1: Fetch ─────────────────────────────────────────────

def run_cmd(cmd, timeout=120):
    """Run a shell command, return success bool."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0
    except Exception as e:
        logger.error("Command failed: %s → %s", cmd[:80], e)
        return False

def fetch_all(tracklist, skip_existing=False):
    """Fetch market, sector, and all stock data in parallel."""
    logger.info("Phase 1: Fetching data...")

    # Market + sector
    run_cmd(f"cd {ROOT} && source .venv/bin/activate && python src/fetch_market.py")
    run_cmd(f"cd {ROOT} && source .venv/bin/activate && python src/sector_scan.py", timeout=180)

    # Stocks in parallel (4 workers)
    codes = [s["code"] for s in tracklist["stocks"]]

    def fetch_one(code):
        ok1 = run_cmd(f"cd {ROOT} && source .venv/bin/activate && python src/fetch.py --code {code}")
        ok2 = run_cmd(f"cd {ROOT} && source .venv/bin/activate && python src/indicators.py --code {code}")
        return code, ok1 and ok2

    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_one, c): c for c in codes}
        for f in as_completed(futures):
            code, ok = f.result()
            results[code] = ok
            if not ok:
                logger.warning("Fetch/indicators failed for %s", code)

    ok_count = sum(results.values())
    logger.info("Phase 1 done: %d/%d stocks fetched", ok_count, len(codes))
    return ok_count == len(codes)

# ── Step 2-4: Generate reports ────────────────────────────────

def generate_all(date_str):
    """Generate all report files using report_lib."""
    from src.report_lib import (load_all_stocks, load_market_index, load_sector_scan,
                                 load_position, simple_strategy, consensus, pe_label,
                                 fmt, date_cn)
    logger.info("Phase 2-4: Generating reports for %s", date_str)

    stocks = load_all_stocks()
    market = load_market_index()
    sector = load_sector_scan()
    idx = market["indices"]

    # ── Individual stock reports ──
    for s in stocks:
        sigs = simple_strategy(s)
        v, avg, buy, hold, sell = consensus(sigs)
        pe_text, pe_color = pe_label(s["pe"])
        pe_s = fmt(s["pe"], ".0f") if s["pe"] else "N/A"
        pb_s = fmt(s["pb"], ".1f") if s["pb"] else "N/A"
        mcap_s = f"{s['mcap']:.0f}亿" if s["mcap"] else "N/A"

        lines = [
            f"# {s['name']}（{s['code']}）每日分析 — {date_cn(date_str)}",
            "", "## 今日走势",
            f"| 收盘 | 涨跌 | 量比 | 换手 |",
            f"|------|------|------|------|",
            f"| {s['price']} | {s['pct_chg']:+.2f}% | {fmt(s.get('vr',1),'.2f')} | {s['turnover']}% |",
            "", f"## 策略信号 ({'3' if s['tier'] in ('core','key') else '2'}策略)",
            f"| 策略 | 信号 | 评分 | 依据 |",
            f"|------|------|------|------|",
        ]
        for sig in sigs:
            lines.append(f"| {sig['display']} | {sig['signal']} | {sig['score']} | {sig['reason']} |")

        lines.append(f"\n**共识**: {v} (buy×{buy} hold×{hold} sell×{sell})，加权{avg:.0f}。\n")
        lines.extend([
            f"## 基本面概览" if s['tier'] in ('core','key') else "## 基本面速览",
            f"| PE | PB | 市值 | 估值 |",
            f"|------|------|------|------|",
            f"| {pe_s} | {pb_s} | {mcap_s} | {pe_text} |", ""])

        # Position block
        if s["has_position"]:
            pos = load_position(s["code"], s["name"])
            if pos:
                p = pos["position"]; lv = pos.get("key_levels", {})
                pnl = (s["price"] - p["buy_price"]) / p["buy_price"] * 100
                stop = lv.get("stop_loss", "N/A")
                lines.extend([
                    "## 持仓策略",
                    f"- **成本**: {p['buy_price']} × {p['shares']}股 = ¥{p['cost']:,.0f}",
                    f"- **现价**: {s['price']}，浮亏 **{pnl:.1f}%**",
                    f"- **止损**: {stop}" + (f" ⛔ 已跌破" if isinstance(stop, (int,float)) and s['price'] < stop else ""),
                    ""])

        # Indicator changes
        lines.extend([
            "## 指标变化",
            f"| 指标 | 数值 | 状态 |",
            f"|------|------|------|",
            f"| MA5/10/20 | {s['ma5']:.1f}/{s['ma10']:.1f}/{s['ma20']:.1f} | {s['trend']}({s['trend_strength']}) |",
            f"| RSI6/12 | {s['rsi6']:.0f}/{s['rsi12']:.0f} | {'超买' if s['rsi12']>70 else '偏强' if s['rsi12']>55 else '中性' if s['rsi12']>45 else '偏弱'} |",
            f"| MACD | hist {s['macd_hist']:.2f} | {'多头' if s['macd_hist']>0 else '空头'} |",
            f"| 乖离率 | {s['bias5']:.1f}% | {'偏高' if s['bias5']>5 else '正常' if s['bias5']>-3 else '偏弱'} |",
            "", "## 操作建议"])

        if s["has_position"]:
            if s["price"] < 50 and s["price"] < s.get("ma20", 99):
                lines.append(f"- ⚠️ 已跌破均线支撑，严格按止损纪律执行")
            else:
                lines.append(f"- 持有观察")
        elif avg >= 55:
            lines.append("- ⚡ 偏多信号，可关注回调买点")
        elif "空头" in s["trend"]:
            lines.append("- 空头趋势，不建议参与")
        else:
            lines.append("- 观望为主")

        out_dir = ROOT / "tracking" / f"{s['code']}-{s['name']}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{date_str}-analysis.md").write_text("\n".join(lines), encoding="utf-8")

    logger.info("  %d individual reports written", len(stocks))

    # ── Market summary ──
    market_md = [
        f"# 大盘总结 — {date_cn(date_str)}", "",
        "## 四大指数",
        "| 指数 | 收盘 | 涨跌 | 5日涨幅 |",
        "|------|------|------|---------|",
    ]
    for k, v in idx.items():
        market_md.append(f"| {v['name']} | {v['close']:.2f} | **{v['pct_chg']:+.2f}%** | {v.get('pct_5d',0):+.2f}% |")

    market_md.extend(["", "## 20大板块排名", ""])
    if sector and sector.get("rankings"):
        market_md.extend([
            "| 排名 | 板块 | 评分 | 均涨幅 | 上涨比 | 最强股 |",
            "|:--:|------|-----|--------|:--:|------|",
        ])
        for i, s in enumerate(sector["rankings"][:10]):
            m = "🥇" if i==0 else ("🥈" if i==1 else ("🥉" if i==2 else f"{i+1}"))
            best = s.get("best_stock_name", "")
            best_pct = s.get("best_stock_pct", 0)
            market_md.append(
                f"| {m} | {s['name']} | {s['score']:.0f} | {s['avg_pct']:+.1f}% | {s['up_ratio']:.0f}% | {best}({best_pct:+.1f}%) |")
        # Bottom 5
        market_md.append("")
        for s in sector["rankings"][-5:]:
            market_md.append(f"|   | {s['name']} | {s['score']:.0f} | {s['avg_pct']:+.1f}% | {s['up_ratio']:.0f}% | |")

    market_md.extend(["", f"---", f"*数据来源：akshare · sector_scan.py · {date_str}收盘*"])
    (ROOT / "tracking/daily/market").mkdir(parents=True, exist_ok=True)
    (ROOT / f"tracking/daily/market/{date_str}.md").write_text("\n".join(market_md), encoding="utf-8")
    logger.info("  Market summary written")

    # ── Positions summary ──
    core = [s for s in stocks if s["tier"]=="core"]
    key = [s for s in stocks if s["tier"]=="key"]
    watch = [s for s in stocks if s["tier"]=="watch"]

    pos_lines = [
        f"# 持仓观察汇总 — {date_cn(date_str)}", "",
        f"> 大盘：上证{idx['000001']['pct_chg']:+.2f}% 深证{idx['399001']['pct_chg']:+.2f}% 创业板{idx['399006']['pct_chg']:+.2f}% 科创{idx['000688']['pct_chg']:+.2f}%", ""]

    for label, group in [("★ 核心持仓", core), ("★ 重点观察", key)]:
        pos_lines.extend([f"## {label}", ""])
        for s in group:
            sigs = simple_strategy(s)
            v, avg, b, h, se = consensus(sigs)
            pe_s = fmt(s["pe"], ".0f") if s["pe"] else "-"
            pos_lines.append(f"### {s['name']}（{s['code']}）")
            pos_lines.append(f"- 收盘: {s['price']} | {s['pct_chg']:+.2f}% | PE={pe_s} | 共识: {v}({avg:.0f})")
            if s["has_position"]:
                pos = load_position(s["code"], s["name"])
                if pos:
                    p = pos["position"]; lv = pos.get("key_levels", {})
                    pnl = (s['price']-p['buy_price'])/p['buy_price']*100
                    pos_lines.append(f"- 持仓: {p['shares']}股 @{p['buy_price']}，浮亏{pnl:.1f}%，止损{lv.get('stop_loss','N/A')}" + (" ⛔已跌破" if s['price']<lv.get('stop_loss',99) else ""))
            pos_lines.append("")

    pos_lines.extend(["## 一般观察", "",
        "| 股票 | 收盘 | 涨跌 | RSI6 | 趋势 | PE | 共识 |",
        "|------|------|------|------|------|----|------|"])
    for s in watch:
        sigs = simple_strategy(s)
        v, avg, _, _, _ = consensus(sigs)
        pe_s = fmt(s["pe"], ".0f") if s["pe"] else "-"
        pos_lines.append(f"| {s['name']}({s['code']}) | {s['price']} | {s['pct_chg']:+.2f}% | {s['rsi6']:.0f} | {s['trend']}({s['trend_strength']}) | {pe_s} | {v}({avg:.0f}) |")

    # PE distribution
    pe_vals = [s['pe'] for s in stocks if s['pe'] and s['pe'] > 0]
    pos_lines.extend(["", "## 估值分布", "",
        f"PE<50(低估): {sum(1 for p in pe_vals if p<50)}只 | "
        f"PE50-100(偏高): {sum(1 for p in pe_vals if 50<=p<100)}只 | "
        f"PE100-200(高估): {sum(1 for p in pe_vals if 100<=p<200)}只 | "
        f"PE>200(严重): {sum(1 for p in pe_vals if p>=200)}只",
        f"\n估值洼地: {', '.join(s['name'] for s in stocks if s['pe'] and s['pe']<50)}",
        f"\n---\n*{len(stocks)}只股票 · {date_str}收盘*"])

    (ROOT / "tracking/daily/positions").mkdir(parents=True, exist_ok=True)
    (ROOT / f"tracking/daily/positions/{date_str}.md").write_text("\n".join(pos_lines), encoding="utf-8")
    logger.info("  Positions summary written (%d stocks)", len(stocks))

    return stocks, market, sector

# ── Step 5: Deploy ────────────────────────────────────────────

def deploy(date_str):
    """Generate HTML, update index, git push."""
    logger.info("Phase 5: Deploying...")
    # Run deploy script
    ok = run_cmd(f"cd {ROOT} && source .venv/bin/activate && python scripts/deploy.py --date {date_str}", timeout=60)
    if not ok:
        logger.warning("deploy.py returned non-zero, trying direct git push")

    # Git push
    cmds = [
        f"cd {ROOT} && git add tracking/ index.html",
        f'cd {ROOT} && git commit -m "deploy: {date_str} daily reports (orchestrated)"',
        f"cd {ROOT} && git push",
    ]
    for cmd in cmds:
        subprocess.run(cmd, shell=True, capture_output=True)
    logger.info("Phase 5 done")

# ── Main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="日报全流程编排")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--skip-fetch", action="store_true", help="跳过数据拉取")
    parser.add_argument("--dry-run", action="store_true", help="只校验不写入")
    parser.add_argument("--no-deploy", action="store_true", help="不部署到GitHub")
    args = parser.parse_args()

    date_str = args.date or datetime.now(_TZ_CN).strftime("%Y-%m-%d")
    logger.info("=== Orchestrate Daily Report: %s ===", date_str)

    # Phase 0
    if not args.skip_fetch:
        fresh = validate_data(date_str)
        if not fresh:
            logger.info("Data stale, re-fetching market...")
            subprocess.run(f"cd {ROOT} && source .venv/bin/activate && python src/fetch_market.py",
                           shell=True, capture_output=True)

    # Phase 1
    tracklist = json.load(open(ROOT / "tracking/tracklist.json"))
    if not args.skip_fetch:
        fetch_all(tracklist)

    if args.dry_run:
        logger.info("Dry run complete, no files written")
        return

    # Phase 2-4
    generate_all(date_str)

    # Phase 5
    if not args.no_deploy:
        deploy(date_str)

    logger.info("=== Done: %s ===", date_str)

if __name__ == "__main__":
    main()
