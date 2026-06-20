#!/usr/bin/env python3
"""
板块强度扫描。基于 sectors.json 中的 20 个细分赛道，计算板块强度排名。
用法: python src/sector_scan.py
输出: data/market/sector_scan.json + tracking/sectors/YYYY-MM-DD-sector-scan.md
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
_TZ_CN = timezone(timedelta(hours=8))

PROJECT = Path(__file__).parent.parent


def load_sectors():
    with open(PROJECT / "tracking" / "sectors.json") as f:
        return json.load(f)


def fetch_all_quotes():
    """拉取全市场行情，返回 {code: {price, pct_chg, amount, volume}}"""
    import akshare as ak
    df = ak.stock_zh_a_spot()
    quotes = {}
    for _, row in df.iterrows():
        try:
            code = str(row["代码"])
            plain = code[2:] if len(code) >= 2 and code[:2] in ("sh", "sz", "bj") else code
            entry = {
                "name": str(row["名称"]),
                "price": float(row["最新价"]),
                "pct_chg": float(row["涨跌幅"]),
                "amount": float(row["成交额"]),
                "volume": float(row["成交量"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "prev_close": float(row["昨收"]),
            }
            quotes[code] = entry
            quotes[plain] = entry  # 也存纯数字代码，兼容 sectors.json
        except (ValueError, KeyError):
            continue
    return quotes


def score_sector(sector, quotes):
    """计算单个板块的强度评分 (0-100)"""
    stocks = sector["stocks"]
    scores = []
    for s in stocks:
        q = quotes.get(s["code"])
        if q:
            scores.append({
                "code": s["code"], "name": s["name"],
                "price": q["price"], "pct_chg": q["pct_chg"],
                "amount": q["amount"] / 1e8,
            })

    if len(scores) < 2:
        return None  # 数据不足

    n = len(scores)
    avg_pct = sum(s["pct_chg"] for s in scores) / n
    up_count = sum(1 for s in scores if s["pct_chg"] > 0)
    up_ratio = up_count / n

    # 平均量比 (简化：用成交额排名近似)
    avg_amount = sum(s["amount"] for s in scores)
    best_pct = max(s["pct_chg"] for s in scores)

    # 评分 = 平均涨幅×0.4 + 上涨占比×0.3 + 量能×0.2 + 最强×0.1
    pct_score = min(100, max(0, 50 + avg_pct * 5))  # 0%→50, +5%→75
    up_score = up_ratio * 100
    amount_score = min(100, avg_amount / 2)  # 2亿→100
    best_score = min(100, 50 + best_pct * 5)

    total = pct_score * 0.4 + up_score * 0.3 + amount_score * 0.2 + best_score * 0.1

    return {
        "id": sector["id"],
        "name": sector["name"],
        "score": round(total, 1),
        "avg_pct": round(avg_pct, 2),
        "up_ratio": round(up_ratio, 2),
        "avg_amount": round(avg_amount, 1),
        "best_stock": max(scores, key=lambda x: x["pct_chg"]),
        "worst_stock": min(scores, key=lambda x: x["pct_chg"]),
        "stock_count": n,
        "stocks": sorted(scores, key=lambda x: -x["pct_chg"]),
    }


def run():
    logger.info("加载板块配置...")
    sectors_data = load_sectors()
    sectors = sectors_data["sectors"]
    logger.info("共 %d 个板块", len(sectors))

    # 收集所有股票代码
    all_codes = set()
    for sec in sectors:
        for s in sec["stocks"]:
            all_codes.add(s["code"])
    logger.info("去重后 %d 只股票", len(all_codes))

    # 拉取行情
    logger.info("拉取全市场行情...")
    quotes = fetch_all_quotes()
    logger.info("获取 %d 只股票行情", len(quotes))

    # 计算各板块评分
    results = []
    missing = []
    for sec in sectors:
        r = score_sector(sec, quotes)
        if r:
            results.append(r)
        else:
            missing.append(sec["name"])

    results.sort(key=lambda x: -x["score"])

    # 输出 JSON
    output = {
        "updated_at": datetime.now(_TZ_CN).isoformat(),
        "sector_count": len(results),
        "missing_sectors": missing,
        "rankings": results,
    }

    out_dir = PROJECT / "data" / "market"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "sector_scan.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    # 生成 Markdown 报告
    today = datetime.now(_TZ_CN).strftime("%Y-%m-%d")
    md = generate_markdown(output, today)
    report_dir = PROJECT / "tracking" / "sectors"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{today}-sector-scan.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)

    # 打印摘要
    print(f"\n🏆 板块强度排名 ({today})")
    print(f"{'排名':<4} {'板块':<16} {'评分':<6} {'均涨幅':<8} {'上涨比':<6} {'最强股'}")
    print("-" * 70)
    for i, r in enumerate(results):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1:2d}."
        print(f"{medal:<4} {r['name']:<16} {r['score']:<6.1f} {r['avg_pct']:>+6.2f}%  {r['up_ratio']:.0%}     {r['best_stock']['name']}({r['best_stock']['pct_chg']:+.1f}%)")

    if missing:
        print(f"\n⚠ 数据不足: {', '.join(missing)}")

    logger.info("JSON → %s", out_dir / "sector_scan.json")
    logger.info("MD   → %s", report_path)
    return output


def generate_markdown(data, today):
    lines = [
        f"# 板块强度扫描 — {today}",
        "",
        f"共 {data['sector_count']} 个板块，{sum(len(r['stocks']) for r in data['rankings'])} 只股票",
        "",
        "## 板块排名",
        "",
        "| 排名 | 板块 | 评分 | 均涨幅 | 上涨比 | 均成交(亿) | 最强股 | 最弱股 |",
        "|------|------|------|--------|--------|-----------|--------|--------|",
    ]

    for i, r in enumerate(data["rankings"]):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else str(i + 1)
        b = r["best_stock"]
        w = r["worst_stock"]
        lines.append(
            f"| {medal} | **{r['name']}** | {r['score']:.1f} | {r['avg_pct']:+.2f}% | {r['up_ratio']:.0%} | {r['avg_amount']:.1f} | {b['name']}({b['pct_chg']:+.1f}%) | {w['name']}({w['pct_chg']:+.1f}%) |"
        )

    lines += [
        "",
        "## 各板块明细",
        "",
    ]

    for r in data["rankings"]:
        lines.append(f"### {r['name']} — {r['score']:.1f} 分")
        lines.append("")
        lines.append(f"均涨幅 {r['avg_pct']:+.2f}% | 上涨 {r['up_ratio']:.0%} | 均成交 {r['avg_amount']:.1f}亿")
        lines.append("")
        lines.append("| 股票 | 代码 | 价格 | 涨跌 | 成交额(亿) |")
        lines.append("|------|------|------|------|-----------|")
        for s in r["stocks"]:
            lines.append(f"| {s['name']} | {s['code']} | {s['price']:.2f} | {s['pct_chg']:+.2f}% | {s['amount']:.1f} |")
        lines.append("")

    if data["missing_sectors"]:
        lines.append(f"⚠ 数据不足: {', '.join(data['missing_sectors'])}")
        lines.append("")

    lines.append(f"---")
    lines.append(f"*数据来源: akshare 新浪财经 | 自动生成于 {today}*")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run()
