import json
import re
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tracking/daily/positions/2026-07-17.md"
REPORT_HTML = ROOT / "tracking/daily/positions/2026-07-17.html"
CONTEXT = ROOT / "data/report_context.json"
TRACKLIST = ROOT / "tracking/tracklist.json"

CARD_HEADINGS = {
    "601138": ("### 工业富联（601138）", "### 1. 工业富联（601138）"),
    "600547": ("### 山东黄金（600547 / 01787.HK）", "### 2. 山东黄金（600547 / 01787.HK）"),
    "002050": ("### 3. 三花智控（002050 / 02050.HK）",),
    "603986": ("### 4. 兆易创新（603986 / 03986.HK）",),
    "09988": ("### 5. 阿里巴巴（09988.HK）",),
    "601899": ("### 紫金矿业（601899）", "### 3A. 紫金矿业（601899）"),
}
HK_POSITION_HEADING = "### 三花智控 H 股（02050.HK）"
HK_UNAVAILABLE_LINE = (
    "- **价量结构**：H股同口径量比、当日量÷MA5、当日量÷MA20、近20日÷前20日、"
    "上涨日÷下跌日均量、MFI、CMF、OBV20、标签与解释标记均为 `unavailable`；"
    "证据缺口 `unavailable`（无 02050.HK `report_context`，不得借用 A 股 002050 指标）"
)
OPEN_LEG_HEADINGS = {
    "02050": (HK_POSITION_HEADING,),
    "601138": CARD_HEADINGS["601138"],
    "600547": CARD_HEADINGS["600547"],
    "601899": CARD_HEADINGS["601899"],
}
HTML_PREFIX = (
    '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>日报 · 2026-07-17</title><style>'
    'body{margin:0;background:#0d1117;color:#c9d1d9;font-family:-apple-system,'
    'BlinkMacSystemFont,"PingFang SC",sans-serif;line-height:1.65}'
    'main{max-width:980px;margin:auto;padding:32px 18px}'
    'h1,h2,h3{color:#f0f6fc}'
    'h2{border-bottom:1px solid #30363d;padding-bottom:8px}'
    'a{color:#58a6ff}'
    'blockquote{border-left:4px solid #58a6ff;margin:16px 0;padding:10px 16px;background:#161b22}'
    'table{border-collapse:collapse;width:100%;display:block;overflow:auto;margin:14px 0}'
    'th,td{border:1px solid #30363d;padding:8px 10px;white-space:nowrap}'
    'th{background:#161b22}'
    'code{background:#161b22;padding:2px 5px;border-radius:4px}'
    '@media(max-width:600px){main{padding:20px 10px}th,td{font-size:12px;padding:6px}}'
    '</style></head><body><main>'
)
HTML_SUFFIX = "</main></body></html>\n"


def _card(report: str, heading: str) -> str:
    start = report.index(heading)
    match = re.search(r"\n#{1,3} ", report[start + len(heading) :])
    end = len(report) if match is None else start + len(heading) + match.start()
    return report[start:end]


def _section_three_cards(report: str) -> dict[str, str]:
    section = report.split("## 三、核心个股深度", 1)[1].split(
        "## 四、A-H 全面对比", 1
    )[0]
    cards = {}
    for heading, markets in re.findall(r"^(### .+?（([^）]+)）)$", section, re.MULTILINE):
        primary_code = re.search(r"\d{5,6}", markets)
        assert primary_code is not None, f"missing code in Section 3 heading: {heading}"
        cards[heading] = primary_code.group()
    return cards


def _number(value: float | None, digits: int = 2, signed: bool = False) -> str:
    if value is None:
        return "`unavailable`"
    return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"


def _expected_line(code: str, context: dict) -> str:
    price_volume = context["stocks"][code]["price_volume"]
    flags = price_volume["interpretation_flags"]
    gaps = price_volume["evidence_gaps"]
    return (
        f"- **价量结构**：量比 {_number(price_volume['intraday_volume_ratio'])}"
        f" / 当日量÷MA5 {_number(price_volume['volume_vs_ma5'])}"
        f" / 当日量÷MA20 {_number(price_volume['volume_vs_ma20'])}"
        f" / 近20日÷前20日 {_number(price_volume['recent20_vs_previous20'])}"
        f" / 上涨日÷下跌日均量 {_number(price_volume['up_down_volume_ratio_90d'])}；"
        f"MFI {_number(price_volume['mfi14'])}"
        f" / CMF {_number(price_volume['cmf20'], signed=price_volume['cmf20'] > 0)}"
        f" / OBV20 `{price_volume['obv_20d_direction']}`；"
        f"标签 {price_volume['price_volume_label']}"
        f" / 解释标记 {'`' + ','.join(flags) + '`' if flags else '[]'}"
        f" / 证据缺口 {'`' + ','.join(gaps) + '`' if gaps else '[]'}"
    )


def _open_position_legs(stock: dict) -> set[str]:
    path = ROOT / "tracking" / f"{stock['code']}-{stock['name']}" / "position.json"
    if not path.exists():
        assert not stock.get("has_position"), f"missing position file for {stock['code']}"
        return set()
    record = json.loads(path.read_text(encoding="utf-8"))
    legs = set()
    for key, value in record.items():
        if key != "position" and not key.endswith("_position"):
            continue
        if not isinstance(value, dict):
            continue
        is_open = value.get("status") == "open" or (
            value.get("status") is None and (value.get("shares") or 0) > 0
        )
        if is_open:
            legs.add(str(value.get("code") or stock["code"]))
    return legs


def test_held_and_core_cards_have_registered_price_volume_without_cross_market_substitution():
    report = REPORT.read_text(encoding="utf-8")
    context = json.loads(CONTEXT.read_text(encoding="utf-8"))
    tracklist = json.loads(TRACKLIST.read_text(encoding="utf-8"))["stocks"]

    applicable = [
        stock
        for stock in tracklist
        if stock.get("has_position") or stock.get("tier") in {"core", "key"}
    ]
    expected_a_codes = {stock["code"] for stock in applicable}
    assert expected_a_codes <= set(CARD_HEADINGS)

    open_legs = {
        leg
        for stock in applicable
        for leg in _open_position_legs(stock)
    }
    assert open_legs <= set(OPEN_LEG_HEADINGS)
    section_three_cards = _section_three_cards(report)
    expected_cards = {
        **section_three_cards,
        **{
            heading: leg
            for leg in open_legs
            for heading in OPEN_LEG_HEADINGS[leg]
        },
    }
    for heading, code in expected_cards.items():
        card = _card(report, heading)
        assert card.count("**价量结构**") == 1
        if code in context["stocks"]:
            assert _expected_line(code, context) in card

    hk_card = _card(report, HK_POSITION_HEADING)
    assert HK_UNAVAILABLE_LINE in hk_card
    assert _expected_line("002050", context) not in hk_card


def test_html_is_byte_for_byte_mechanical_render_of_markdown():
    markdown_text = REPORT.read_text(encoding="utf-8")
    rendered_body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    expected = HTML_PREFIX + rendered_body + HTML_SUFFIX
    assert REPORT_HTML.read_bytes() == expected.encode("utf-8")
