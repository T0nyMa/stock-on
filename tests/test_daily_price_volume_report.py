import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "tracking/daily/positions/2026-07-17.md"
CONTEXT = ROOT / "data/report_context.json"
TRACKLIST = ROOT / "tracking/tracklist.json"

CORE_CODES = {"601138", "600547", "002050", "603986", "09988"}
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
    "证据缺口 `hk_price_volume_unavailable`（不得借用 A 股 002050 指标）"
)


def _card(report: str, heading: str) -> str:
    start = report.index(heading)
    match = re.search(r"\n#{1,3} ", report[start + len(heading) :])
    end = len(report) if match is None else start + len(heading) + match.start()
    return report[start:end]


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
        f" / 解释标记 {'`' + ','.join(flags) + '`' if flags else '无'}"
        f" / 证据缺口 {'`' + ','.join(gaps) + '`' if gaps else '无'}"
    )


def test_held_and_core_cards_have_registered_price_volume_without_cross_market_substitution():
    report = REPORT.read_text(encoding="utf-8")
    context = json.loads(CONTEXT.read_text(encoding="utf-8"))
    tracklist = json.loads(TRACKLIST.read_text(encoding="utf-8"))["stocks"]

    expected_codes = CORE_CODES | {
        stock["code"] for stock in tracklist if stock.get("has_position")
    }
    assert expected_codes == set(CARD_HEADINGS) | {"002050"}

    for code, headings in CARD_HEADINGS.items():
        expected_line = _expected_line(code, context)
        for heading in headings:
            card = _card(report, heading)
            assert card.count("**价量结构**") == 1
            assert expected_line in card

    hk_card = _card(report, HK_POSITION_HEADING)
    assert hk_card.count("**价量结构**") == 1
    assert HK_UNAVAILABLE_LINE in hk_card
    assert _expected_line("002050", context) not in hk_card
