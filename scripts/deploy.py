#!/usr/bin/env python3
"""发布日报到 GitHub Pages — 生成 HTML + 更新 index.html。
用法: python scripts/deploy.py [--date YYYY-MM-DD]
"""
import argparse, json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.report_lib import (load_all_stocks, load_market_index, load_sector_scan,
                             load_position, simple_strategy, consensus, pe_label,
                             fmt, date_cn, today_str, date_md_heading)
from src.chart_html import (sector_ranking_chart, pe_distribution_chart,
                             consensus_meter, sparkline, kpi_card)

def gen_market_html(date_str):
    """大盘总结 HTML."""
    market = load_market_index()
    sector = load_sector_scan()
    idx = market["indices"]

    # Sector chart
    sector_chart = ""
    if sector and sector.get("rankings"):
        sector_chart = ('<div class="card"><h2>板块排名</h2>'
                        + sector_ranking_chart(sector["rankings"], 20)
                        + '</div>')

    # Index KPI cards
    kpi_cards = []
    for k in ["000001", "399001", "399006", "000688"]:
        v = idx.get(k, {})
        kpi_cards.append(kpi_card(v.get("name", "?"), f'{v.get("close",0):.0f}', v.get("pct_chg",0)))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>大盘总结 — {date_cn(date_str)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 760px; margin:0 auto; padding:24px 16px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color:#fff; padding:32px; border-radius:12px; margin-bottom:24px; }}
  .header h1 {{ font-size:24px; margin-bottom:8px; }}
  .header .date {{ font-size:14px; color:#8892b0; }}
  .card {{ background:#fff; border-radius:10px; padding:24px; margin-bottom:16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card h2 {{ font-size:18px; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #eee; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin-bottom:12px; }}
  th {{ background:#f8f9fa; padding:10px 12px; text-align:left; font-weight:500; color:#666; }}
  td {{ padding:10px 12px; border-bottom:1px solid #f0f0f0; }}
  .up {{ color:#27ae60; font-weight:600; }} .down {{ color:#e74c3c; font-weight:600; }}
  .kpi-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }}
  .footer {{ text-align:center; color:#999; font-size:12px; margin-top:24px; padding:16px; }}
</style></head><body><div class="container">
<div class="header"><h1>大盘总结</h1><div class="date">{date_cn(date_str)}</div></div>
<div class="card">
<h2>四大指数</h2>
<div class="kpi-row">{"".join(kpi_cards)}</div>
<table>
<tr><th>指数</th><th>收盘</th><th>开盘</th><th>最高</th><th>最低</th><th>涨跌</th><th>5日涨幅</th></tr>
"""
    for k in ["000001", "399001", "399006", "000688"]:
        v = idx.get(k, {})
        cls = "up" if v.get("pct_chg",0) > 0 else "down"
        html += f"""<tr><td>{v.get('name','')}</td><td>{v.get('close',0):.2f}</td>
<td>{v.get('open',0):.2f}</td><td>{v.get('high',0):.2f}</td><td>{v.get('low',0):.2f}</td>
<td class="{cls}">{v.get('pct_chg',0):+.2f}%</td><td class="{cls}">{v.get('pct_5d',0):+.2f}%</td></tr>"""

    html += "</table></div>"
    html += sector_chart
    html += f'<div class="footer">Stock-On · {date_cn(date_str)}收盘 · 来源 akshare</div>'
    html += '</div></body></html>'

    out = ROOT / f"tracking/daily/market/{date_str}.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Market HTML → {out}")

def gen_positions_html(date_str):
    """持仓汇总 HTML（含图表）."""
    stocks = load_all_stocks()
    core = [s for s in stocks if s["tier"]=="core"]
    key = [s for s in stocks if s["tier"]=="key"]
    watch = [s for s in stocks if s["tier"]=="watch"]

    pe_chart = pe_distribution_chart(stocks)

    alerts = []
    for s in stocks:
        if s["has_position"]:
            pos = load_position(s["code"], s["name"])
            if pos:
                lv = pos.get("key_levels", {})
                stop = lv.get("stop_loss", 99)
                if s["price"] < stop:
                    alerts.append(f'{s["name"]}({s["price"]} 破止损{stop})')

    alert_html = ""
    if alerts:
        alert_html = '<div class="alert"><strong>⛔ 止损警报</strong>：' + ' · '.join(alerts) + '</div>'

    def stock_card(s):
        sigs = simple_strategy(s)
        v, avg, b, h, se = consensus(sigs)
        pe_t, _ = pe_label(s["pe"])
        pe_d = fmt(s["pe"], ".0f") if s["pe"] else "N/A"
        pb_d = fmt(s["pb"], ".1f") if s["pb"] else "N/A"
        meter = consensus_meter(b, h, se)
        has_pos = s["has_position"]

        c = f'<div class="stock-name">{s["name"]}<span style="color:#999;font-weight:400;font-size:13px;margin-left:8px;">{s["code"]}</span>'
        if has_pos:
            try:
                pos = load_position(s["code"], s["name"])
                p = pos["position"]; lv = pos.get("key_levels",{})
                pnl = (s["price"]-p["buy_price"])/p["buy_price"]*100
                c += f' — 持有{p["shares"]}股 · <span style="color:#e74c3c">浮亏{pnl:.1f}%</span>'
            except: pass
        c += '</div>'
        c += f"""<div class="meta-grid">
        <div class="meta-item"><div class="lbl">收盘</div><div class="val {'up' if s['pct_chg']>0 else 'down'}">{fmt(s['price'],'.2f')} <small>{s['pct_chg']:+.2f}%</small></div></div>
        <div class="meta-item"><div class="lbl">PE</div><div class="val">{pe_d}</div></div>
        <div class="meta-item"><div class="lbl">PB</div><div class="val">{pb_d}</div></div>
        <div class="meta-item"><div class="lbl">趋势</div><div class="val">{s['trend']}({s['trend_strength']})</div></div>
        <div class="meta-item"><div class="lbl">RSI6</div><div class="val">{fmt(s['rsi6'],'.0f')}</div></div>
        <div class="meta-item"><div class="lbl">共识</div><div class="val">{v}({avg:.0f})</div></div>
        </div>"""
        c += f'<div style="margin-bottom:8px">{meter}</div>'
        if has_pos:
            pos = load_position(s["code"], s["name"])
            if pos:
                p = pos["position"]; lv = pos.get("key_levels",{})
                stop = lv.get("stop_loss","?")
                breached = s["price"] < stop
                c += f'<p style="color:#e74c3c;font-weight:600">{"⛔" if breached else "⚡"} 止损{stop} | 亏损¥{abs(p["unrealized_pnl"]):,.0f}</p>'
        return c

    core_cards = "".join(f'<div class="card core"><h2>★ 核心持仓</h2>{stock_card(s)}</div>' for s in core)
    key_cards = "".join(f'<div class="card key"><h2>★ 重点观察</h2>{stock_card(s)}</div>' for s in key)

    # Watch table
    watch_rows = ""
    for s in watch:
        sigs = simple_strategy(s)
        v, avg, _, _, _ = consensus(sigs)
        pe_d = fmt(s["pe"], ".0f") if s["pe"] else "-"
        pb_d = fmt(s["pb"], ".1f") if s["pb"] else "-"
        cls = "up" if s['pct_chg'] > 0 else "down"
        watch_rows += f"""<tr><td><strong>{s['name']}</strong> <span style="color:#999">{s['code']}</span></td>
        <td>{fmt(s['price'],'.2f')}</td><td class="{cls}">{s['pct_chg']:+.2f}%</td>
        <td>{fmt(s['rsi6'],'.0f')}</td><td>{s['trend']}({s['trend_strength']})</td><td>{pe_d}</td><td>{pb_d}</td><td>{v}({avg:.0f})</td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>持仓观察汇总 — {date_cn(date_str)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 960px; margin:0 auto; padding:24px 16px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color:#fff; padding:32px; border-radius:12px; margin-bottom:24px; }}
  .header h1 {{ font-size:24px; margin-bottom:8px; }}
  .header .date {{ font-size:14px; color:#8892b0; }}
  .alert {{ background: #fde8e8; border-left: 4px solid #e74c3c; padding: 12px 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px; }}
  .card {{ background:#fff; border-radius:10px; padding:24px; margin-bottom:16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card h2 {{ font-size:18px; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #eee; }}
  .card.core h2 {{ color:#e74c3c; border-color:#fde8e8; }}
  .card.key h2 {{ color:#e67e22; border-color:#fef0e6; }}
  .stock-name {{ font-size:16px; font-weight:600; margin-bottom:12px; }}
  .meta-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(140px,1fr)); gap:10px; margin-bottom:12px; }}
  .meta-item {{ background:#f8f9fa; padding:10px 12px; border-radius:6px; }}
  .meta-item .lbl {{ font-size:11px; color:#999; }}
  .meta-item .val {{ font-size:16px; font-weight:600; }}
  .val.up {{ color:#27ae60; }} .val.down {{ color:#e74c3c; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#f8f9fa; padding:8px 10px; text-align:left; font-weight:500; color:#666; }}
  td {{ padding:8px 10px; border-bottom:1px solid #f0f0f0; }}
  .footer {{ text-align:center; color:#999; font-size:12px; margin-top:24px; padding:16px; }}
</style></head><body><div class="container">
<div class="header"><h1>持仓观察汇总</h1><div class="date">{date_cn(date_str)}</div></div>
{alert_html}
{core_cards}
{key_cards}
<div class="card"><h2>一般观察</h2>
<table><thead><tr><th>股票</th><th>收盘</th><th>涨跌</th><th>RSI6</th><th>趋势</th><th>PE</th><th>PB</th><th>共识</th></tr></thead><tbody>
{watch_rows}</tbody></table></div>
<div class="card"><h2>估值分布</h2>
{pe_chart}
<p>估值洼地：{', '.join(s['name'] for s in stocks if s['pe'] and s['pe']<50)}</p>
</div>
<div class="footer">Stock-On · 数据截至{date_cn(date_str)}收盘 · {len(stocks)}只股票</div>
</div></body></html>"""

    out = ROOT / f"tracking/daily/positions/{date_str}.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Positions HTML → {out}")

def gen_sector_html(date_str):
    """板块扫描 HTML（含排名柱状图）."""
    sector = load_sector_scan()
    if not sector or not sector.get("rankings"):
        return

    chart = sector_ranking_chart(sector["rankings"], 20)

    rows = ""
    for i, s in enumerate(sector["rankings"][:20]):
        m = "🥇" if i==0 else ("🥈" if i==1 else ("🥉" if i==2 else str(i+1)))
        pct = s.get("avg_pct", 0)
        cls = "up" if pct > 0 else "down"
        rows += f"""<tr><td>{m}</td><td><strong>{s['name']}</strong></td>
        <td>{s['score']:.0f}</td><td class="{cls}">{pct:+.1f}%</td>
        <td>{s['up_ratio']:.0f}%</td><td>{s.get('best_stock_name','')}({s.get('best_stock_pct',0):+.1f}%)</td></tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>板块扫描 — {date_cn(date_str)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 760px; margin:0 auto; padding:24px 16px; }}
  .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color:#fff; padding:32px; border-radius:12px; margin-bottom:24px; }}
  .header h1 {{ font-size:24px; margin-bottom:8px; }}
  .header .date {{ font-size:14px; color:#8892b0; }}
  .card {{ background:#fff; border-radius:10px; padding:24px; margin-bottom:16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card h2 {{ font-size:18px; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #eee; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ background:#f8f9fa; padding:8px 10px; text-align:left; font-weight:500; color:#666; }}
  td {{ padding:8px 10px; border-bottom:1px solid #f0f0f0; }}
  .up {{ color:#27ae60; font-weight:600; }} .down {{ color:#e74c3c; font-weight:600; }}
  .footer {{ text-align:center; color:#999; font-size:12px; margin-top:24px; padding:16px; }}
</style></head><body><div class="container">
<div class="header"><h1>板块强度扫描</h1><div class="date">{date_cn(date_str)} · 20个AI/科技板块</div></div>
<div class="card"><h2>排名柱状图</h2>{chart}</div>
<div class="card"><h2>完整排名</h2>
<table><thead><tr><th>#</th><th>板块</th><th>评分</th><th>均涨幅</th><th>上涨比</th><th>最强股</th></tr></thead><tbody>
{rows}</tbody></table></div>
<div class="footer">Stock-On · {date_cn(date_str)} · 来源 sector_scan.py</div>
</div></body></html>"""

    (ROOT / "tracking/sectors").mkdir(parents=True, exist_ok=True)
    out = ROOT / f"tracking/sectors/{date_str}-sector-scan.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Sector HTML → {out}")

def update_index_html(date_str):
    """整文件重写 index.html."""
    from src.report_lib import load_tracklist
    import glob as g

    # Scan available dates
    dates = set()
    for f in g.glob(str(ROOT / "tracking/daily/market/20*.html")):
        dates.add(os.path.basename(f)[:10])
    dates = sorted(dates, reverse=True)

    # Weekly reports
    weeklies = []
    for f in g.glob(str(ROOT / "tracking/weekly/20*.html")):
        weeklies.append(os.path.basename(f)[:10])
    weeklies = sorted(weeklies, reverse=True)

    sections = []
    for d in dates:
        label = date_md_heading(d)
        sections.append(f"""<div class="section">
  <h2>{label}</h2>
  <a class="link" href="tracking/daily/market/{d}.html">
    <span class="title">📊 大盘总结 <span class="tag market">market</span></span>
    <span class="date">{d}</span>
  </a>
  <a class="link" href="tracking/daily/positions/{d}.html">
    <span class="title">📋 持仓观察汇总 <span class="tag positions">positions</span></span>
    <span class="date">{d}</span>
  </a>
</div>""")

    weekly_sec = ""
    if weeklies:
        wlinks = "\n".join(
            f'  <a class="link" href="tracking/weekly/{w}.html"><span class="title">📈 周度总结 <span class="tag weekly">weekly</span></span><span class="date">{w}</span></a>'
            for w in weeklies)
        weekly_sec = f'<div class="section"><h2>周报</h2>\n{wlinks}\n</div>'

    # Stock links
    tl = load_tracklist()
    stock_links = []
    latest = dates[0] if dates else date_str
    for s in tl["stocks"]:
        tc = {"core":"background:#2a1f1f;color:#f78166;",
              "key":"background:#2a1f0a;color:#e67e22;",
              "watch":"background:#1f2a37;color:#58a6ff;"}.get(s["tier"],"")
        stock_links.append(
            f'  <a class="link" href="tracking/{s["code"]}-{s["name"]}/{latest}-analysis.md">'
            f'<span class="title">{s["name"]} {s["code"]} <span class="tag" style="{tc}">{s["tier"]}</span></span></a>')

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock-On · 股票追踪日报</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif; background: #0d1117; color: #c9d1d9; max-width: 720px; margin: 0 auto; padding: 40px 20px; }}
  h1 {{ font-size:28px; margin-bottom:8px; color:#f0f6fc; }}
  .sub {{ color:#8b949e; margin-bottom:32px; font-size:14px; }}
  .section {{ margin-bottom:28px; }}
  .section h2 {{ font-size:16px; color:#8b949e; border-bottom:1px solid #21262d; padding-bottom:8px; margin-bottom:12px; }}
  .link {{ display:flex; align-items:center; justify-content:space-between; padding:10px 14px; background:#161b22; border:1px solid #21262d; border-radius:6px; margin-bottom:6px; text-decoration:none; color:#c9d1d9; }}
  .link:hover {{ border-color:#58a6ff; }}
  .link .title {{ font-weight:500; }}
  .link .date {{ color:#8b949e; font-size:13px; }}
  .tag {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; margin-left:8px; }}
  .tag.market {{ background:#1f2a37; color:#58a6ff; }} .tag.positions {{ background:#2a1f1f; color:#f78166; }} .tag.weekly {{ background:#1f2a1f; color:#3fb950; }}
  .footer {{ margin-top:40px; padding-top:16px; border-top:1px solid #21262d; font-size:12px; color:#8b949e; }}
  .footer a {{ color:#58a6ff; }}
</style></head><body>
<h1>Stock-On</h1>
<p class="sub">股票追踪日报 · 基于 Python + CSS Charts · 最新交易日 {latest}</p>
{''.join(sections)}
{weekly_sec}
<div class="section"><h2>单股分析 ({latest})</h2>
{''.join(stock_links)}
</div>
<div class="footer"><a href="https://github.com/t0nyma/stock-on">GitHub</a> · 自动生成于 {date_str}</div>
</body></html>"""

    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(f"  index.html updated ({len(dates)} dates, {len(stock_links)} stocks)")

# ── Main ──
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    date_str = args.date or today_str()

    print(f"Deploying reports for {date_str}...")
    gen_market_html(date_str)
    gen_positions_html(date_str)
    gen_sector_html(date_str)
    update_index_html(date_str)

    # Git push
    import subprocess
    for cmd in [
        f"cd {ROOT} && git add tracking/ index.html",
        f'cd {ROOT} && git commit -m "deploy: {date_str} reports with charts"',
        f"cd {ROOT} && git push",
    ]:
        subprocess.run(cmd, shell=True, capture_output=True)
    print("Deploy complete.")

if __name__ == "__main__":
    main()
