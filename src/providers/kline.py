"""K线 Provider: 腾讯→东财降级链，A+H统一入口。"""
from __future__ import annotations

import logging
from typing import Optional

from .http_client import get_json
from .models import KlineRow, EvidenceMeta, tencent_a_code, tencent_hk_code, em_secid

logger = logging.getLogger(__name__)


class KlineProvider:
    """日K线数据，腾讯→东财降级。A/H/US自动路由。"""

    def get_daily(self, code: str, limit: int = 60) -> tuple[list[KlineRow], EvidenceMeta]:
        """获取日K线，返回 (kline_list, evidence)。"""
        meta = EvidenceMeta(source_chain=[])

        # 港股走腾讯 K 线
        if code.upper().startswith("HK"):
            rows = self._try_tencent_hk(code, limit)
            if rows:
                meta.source = "tencent"
                meta.source_chain = ["tencent:ok"]
                return rows, meta
            rows = self._try_eastmoney(code, limit)
            if rows:
                meta.source = "eastmoney"
                meta.source_chain = ["tencent:fail", "eastmoney:ok"]
                return rows, meta
            meta.source_chain = ["tencent:fail", "eastmoney:fail"]
            meta.gaps = ["kline"]
            meta.quality_score = 0
            return [], meta

        # A股: 腾讯→东财
        rows = self._try_tencent(code, limit)
        if rows:
            meta.source = "tencent"
            meta.source_chain = ["tencent:ok"]
            return rows, meta

        rows = self._try_eastmoney(code, limit)
        if rows:
            meta.source = "eastmoney"
            meta.source_chain = ["tencent:fail", "eastmoney:ok"]
            return rows, meta

        meta.source_chain = ["tencent:fail", "eastmoney:fail"]
        meta.gaps = ["kline"]
        meta.quality_score = 0
        return [], meta

    def _try_tencent(self, code: str, limit: int) -> Optional[list[KlineRow]]:
        tc = tencent_a_code(code)
        try:
            data = get_json(
                "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                params={"param": f"{tc},day,,,{limit},qfq"},
                headers={"Referer": "https://gu.qq.com/"},
                timeout=15,
            )
            payload = (data.get("data") or {}).get(tc) or {}
            rows = payload.get("qfqday") or payload.get("day") or []
            return [_parse_tencent_kline_row(r) for r in rows if len(r) >= 6]
        except Exception as e:
            logger.debug("腾讯K线 %s 失败: %s", code, e)
            return None

    def _try_tencent_hk(self, code: str, limit: int) -> Optional[list[KlineRow]]:
        tc = tencent_hk_code(code)
        try:
            data = get_json(
                "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
                params={"param": f"{tc},day,,,{limit},qfq"},
                headers={"Referer": "https://gu.qq.com/"},
                timeout=15,
            )
            payload = (data.get("data") or {}).get(tc) or {}
            rows = payload.get("qfqday") or payload.get("day") or []
            return [_parse_tencent_kline_row(r) for r in rows if len(r) >= 6]
        except Exception as e:
            logger.debug("腾讯港股K线 %s 失败: %s", code, e)
            return None

    def _try_eastmoney(self, code: str, limit: int) -> Optional[list[KlineRow]]:
        try:
            secid = em_secid(code)
            data = get_json(
                "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                params={
                    "secid": secid,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "klt": "101",
                    "fqt": "1",
                    "lmt": limit,
                },
                timeout=15,
            )
            rows = (data.get("data") or {}).get("klines") or []
            result = []
            prev_close = None
            for r in rows[-limit:]:
                parts = str(r).split(",")
                if len(parts) < 7:
                    continue
                close = _safe_float(parts[2])
                pct_chg = None
                if prev_close and prev_close > 0 and close is not None:
                    pct_chg = (close - prev_close) / prev_close * 100
                prev_close = close
                result.append(KlineRow(
                    date=parts[0],
                    open=_safe_float(parts[1]) or 0,
                    close=close or 0,
                    high=_safe_float(parts[3]) or 0,
                    low=_safe_float(parts[4]) or 0,
                    volume=_safe_float(parts[5]) or 0,
                    amount=_safe_float(parts[6]) or 0,
                    pct_chg=pct_chg,
                ))
            return result if result else None
        except Exception as e:
            logger.debug("东财K线 %s 失败: %s", code, e)
            return None


def _parse_tencent_kline_row(row: list) -> KlineRow:
    """腾讯K线行: [date, open, close, high, low, volume, ...]"""
    close = _safe_float(row[2]) or 0
    open_v = _safe_float(row[1]) or 0
    prev_close = close  # approximate, will be corrected by caller
    pct_chg = ((close - open_v) / open_v * 100) if open_v > 0 else None
    return KlineRow(
        date=str(row[0]),
        open=open_v,
        close=close,
        high=_safe_float(row[3]) or 0,
        low=_safe_float(row[4]) or 0,
        volume=_safe_float(row[5]) or 0,
        amount=0.0,
        pct_chg=pct_chg,
    )


def _safe_float(v) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
