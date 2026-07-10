"""统一数据模型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

_TZ_CN = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(_TZ_CN).isoformat()


@dataclass
class QuoteData:
    """实时行情快照。"""
    symbol: str
    name: str = ""
    market: str = ""           # SH / SZ / HK / US
    price: float = 0.0
    prev_close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: float = 0.0
    amount: float = 0.0        # 成交额(元)
    turnover_rate: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    market_cap: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    ytd: Optional[float] = None
    currency: str = "CNY"
    source: str = ""
    source_chain: list[str] = field(default_factory=list)
    trade_date: str = field(default_factory=lambda: datetime.now(_TZ_CN).strftime("%Y-%m-%d"))


@dataclass
class KlineRow:
    """单日K线。"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float
    amount: float = 0.0
    pct_chg: Optional[float] = None


@dataclass
class IndexData:
    """指数行情。"""
    symbol: str
    name: str
    price: float = 0.0
    change_pct: Optional[float] = None
    volume: float = 0.0
    amount: float = 0.0


@dataclass
class SectorData:
    """板块排名数据。"""
    name: str
    code: str = ""
    avg_pct: float = 0.0
    up_ratio: float = 0.0
    leader: str = ""
    leader_pct: float = 0.0


@dataclass
class EvidenceMeta:
    """证据质量元数据。"""
    source: str = ""
    source_chain: list[str] = field(default_factory=list)
    fetched_at: str = field(default_factory=_now)
    latency_ms: float = 0.0
    gaps: list[str] = field(default_factory=list)
    quality_score: int = 100

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_chain": self.source_chain,
            "fetched_at": self.fetched_at,
            "latency_ms": self.latency_ms,
            "gaps": self.gaps,
            "quality_score": self.quality_score,
            "stale": False,
        }


def tencent_a_code(code: str) -> str:
    """纯数字代码 → 腾讯格式 (sh600519 / sz000651)。"""
    code = code.strip().upper()
    if code.startswith("HK"):
        return f"hk{code[2:].zfill(5)}"
    if code.startswith(("SH", "SZ")):
        return code.lower()
    if code[0] in ("6", "5", "9"):
        return f"sh{code}"
    if code[0] in ("0", "3"):
        return f"sz{code}"
    if code[0] in ("4", "8"):
        return f"bj{code}"
    return code.lower()


def tencent_hk_code(code: str) -> str:
    """港股代码 → 腾讯格式 (hk00700)。"""
    code = code.strip().upper()
    if code.startswith("HK"):
        return f"hk{code[2:].zfill(5)}"
    return f"hk{code.zfill(5)}"


def em_secid(code: str) -> str:
    """纯数字代码 → 东财 secid (1.600519 / 0.000651 / 116.00700)。"""
    code = code.strip().upper()
    if code.startswith("HK"):
        raw = code[2:]
        return f"116.{raw.lstrip('0') or '0'}"
    if code[0] in ("6", "5", "9"):
        return f"1.{code}"
    if code[0] in ("0", "3"):
        return f"0.{code}"
    return f"0.{code}"


def sina_code(code: str) -> str:
    """纯数字代码 → 新浪格式 (sh600519 / sz000651 / hk00700)。"""
    return tencent_a_code(code)


def detect_market(code: str) -> str:
    """检测市场。"""
    code = code.strip().upper()
    if code.startswith("HK"):
        return "HK"
    if code[0] in ("6", "5"):
        return "SH"
    if code[0] in ("0", "3"):
        return "SZ"
    if code[0] in ("4", "8"):
        return "BJ"
    return ""
