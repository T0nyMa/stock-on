"""纯 CSS/SVG 图表生成。零外部依赖，GitHub Pages 静态渲染。"""
import math

CHART_CSS = """
<style>
.hbar-wrap { margin:4px 0; display:flex; align-items:center; gap:8px; }
.hbar-label { width:80px; font-size:12px; text-align:right; flex-shrink:0; color:#666; }
.hbar-track { flex:1; height:18px; background:#f0f0f0; border-radius:3px; overflow:hidden; }
.hbar-fill { height:100%; border-radius:3px; transition:width .3s; display:flex; align-items:center; padding-left:6px; font-size:11px; color:#fff; font-weight:600; min-width:20px; }
.spark-wrap { display:inline-block; vertical-align:middle; }
.consensus-bar { height:24px; border-radius:4px; display:flex; overflow:hidden; font-size:10px; color:#fff; font-weight:600; }
.consensus-bar .buy { background:#27ae60; }
.consensus-bar .hold { background:#f39c12; }
.consensus-bar .sell { background:#e74c3c; }
.pe-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin:12px 0; }
.pe-cell { text-align:center; padding:12px 8px; border-radius:8px; }
.pe-cell .count { font-size:24px; font-weight:700; }
.pe-cell .label { font-size:11px; color:#888; margin-top:2px; }
.pe-cell.c1{background:#e8f5e9;color:#27ae60}.pe-cell.c2{background:#fef9e7;color:#e67e22}
.pe-cell.c3{background:#fde8e8;color:#e74c3c}.pe-cell.c4{background:#fadbd8;color:#c0392b}
.kpi-card { background:#f8f9fa; border-radius:8px; padding:14px; text-align:center; }
.kpi-card .val { font-size:22px; font-weight:700; }
.kpi-card .lbl { font-size:11px; color:#999; margin-top:2px; }
.kpi-card .trend { font-size:12px; margin-top:4px; }
</style>
"""

def horizontal_bar(items, width=600):
    """横向柱状图。items: [{"label":"","value":92.7,"color":"#27ae60"},...]"""
    if not items:
        return ""
    max_v = max(it["value"] for it in items) or 1
    rows = []
    for it in items:
        pct = min(it["value"] / max_v * 100, 100)
        color = it.get("color", "#3498db")
        rows.append(
            f'<div class="hbar-wrap">'
            f'<span class="hbar-label">{it["label"]}</span>'
            f'<div class="hbar-track"><div class="hbar-fill" style="width:{pct:.0f}%;background:{color}">'
            f'{it["value"]:.0f}</div></div></div>')
    return CHART_CSS + "\n".join(rows)

def sector_ranking_chart(rankings, top_n=10):
    """板块排名柱状图。rankings: list of sector dicts with name, score."""
    colors = ["#27ae60", "#2ecc71", "#f1c40f", "#f39c12", "#e67e22",
              "#e74c3c", "#c0392b", "#8e44ad", "#3498db", "#1abc9c"]
    items = []
    for i, s in enumerate(rankings[:top_n]):
        name = s.get("name", s.get("板块", "?"))
        score = s.get("score", 0)
        color = colors[min(i, len(colors)-1)]
        items.append({"label": name, "value": score, "color": color})
    return horizontal_bar(items)

def pe_distribution_chart(stocks):
    """PE分布图。stocks: list of dicts with pe field."""
    buckets = {"<30": 0, "30-50": 0, "50-100": 0, "100-200": 0, ">200": 0}
    for s in stocks:
        pe = s.get("pe")
        if pe is None: continue
        if pe < 30: buckets["<30"] += 1
        elif pe < 50: buckets["30-50"] += 1
        elif pe < 100: buckets["50-100"] += 1
        elif pe < 200: buckets["100-200"] += 1
        else: buckets[">200"] += 1

    cells = []
    for i, (label, count) in enumerate(buckets.items()):
        cells.append(f'<div class="pe-cell c{i+1}"><div class="count">{count}</div><div class="label">{label}</div></div>')

    return CHART_CSS + f'<div class="pe-grid">{"".join(cells)}</div>'

def sparkline(values, width=100, height=30, color="#27ae60", negative_color="#e74c3c"):
    """SVG迷你走势线。values: list of floats."""
    if not values or len(values) < 2:
        return ""
    mn = min(values)
    mx = max(values)
    rng = mx - mn or 1
    n = len(values)
    step = width / (n - 1)

    points = []
    for i, v in enumerate(values):
        x = i * step
        y = height - (v - mn) / rng * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")

    line_color = color if values[-1] >= values[0] else negative_color
    svg = (f'<svg class="spark-wrap" width="{width}" height="{height}">'
           f'<polyline points="{" ".join(points)}" fill="none" stroke="{line_color}" stroke-width="1.5"/>'
           f'</svg>')
    return svg

def consensus_meter(buy, hold, sell, width=200):
    """策略共识仪表。buy/hold/sell: int counts."""
    total = buy + hold + sell or 1
    bp = buy / total * 100
    hp = hold / total * 100
    sp = sell / total * 100
    parts = []
    if buy: parts.append(f'<div class="buy" style="width:{bp:.0f}%">{buy}买</div>')
    if hold: parts.append(f'<div class="hold" style="width:{hp:.0f}%">{hold}持</div>')
    if sell: parts.append(f'<div class="sell" style="width:{sp:.0f}%">{sell}卖</div>')
    return CHART_CSS + f'<div class="consensus-bar" style="width:{width}px">{"".join(parts)}</div>'

def kpi_card(label, value, trend=None, up_good=True):
    """指标卡片。trend: +/- number or None."""
    color = ""
    if trend is not None:
        if (trend > 0 and up_good) or (trend < 0 and not up_good):
            color = "color:#27ae60"
        elif trend != 0:
            color = "color:#e74c3c"
    trend_html = f'<div class="trend" style="{color}">{trend:+.1f}%</div>' if trend is not None else ""
    return f'<div class="kpi-card"><div class="val">{value}</div><div class="lbl">{label}</div>{trend_html}</div>'
