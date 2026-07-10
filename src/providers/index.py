"""指数/板块 Provider: 东财 API。"""
from __future__ import annotations

import logging
from typing import Optional

from .http_client import get_json, rate_limit
from .models import IndexData, SectorData

logger = logging.getLogger(__name__)

A_INDEX_SECIDS = "1.000001,0.399001,0.399006,1.000300,1.000688,0.399005"
A_INDEX_NAMES = {
    "000001": "上证指数", "399001": "深证成指", "399006": "创业板指",
    "000300": "沪深300", "000688": "科创50", "399005": "中小100",
}


class IndexProvider:
    """指数行情和板块排名。"""

    def get_a_indices(self) -> list[IndexData]:
        """A股主要指数行情。"""
        try:
            data = get_json(
                "https://push2.eastmoney.com/api/qt/ulist.np/get",
                params={
                    "fltt": "2",
                    "secids": A_INDEX_SECIDS,
                    "fields": "f2,f3,f4,f5,f6,f12,f14",
                },
                timeout=10,
            )
            rows = (data.get("data") or {}).get("diff") or []
            result = []
            for r in rows:
                code = str(r.get("f12", ""))
                result.append(IndexData(
                    symbol=code,
                    name=A_INDEX_NAMES.get(code, r.get("f14", "")),
                    price=_safe_float(r.get("f2")) or 0,
                    change_pct=_safe_float(r.get("f3")),
                    volume=_safe_float(r.get("f5")) or 0,
                    amount=_safe_float(r.get("f6")) or 0,
                ))
            return result
        except Exception as e:
            logger.warning("A股指数获取失败: %s", e)
            return []

    def get_sector_rankings(self, board_type: str = "industry", limit: int = 20) -> list[SectorData]:
        """行业/概念板块排名。board_type: 'industry' | 'concept'"""
        fs = "m:90+t2" if board_type == "industry" else "m:90+t3"
        try:
            rate_limit(1.0)
            data = get_json(
                "https://push2.eastmoney.com/api/qt/clist/get",
                params={
                    "pn": "1",
                    "pz": str(limit),
                    "fid": "f3",
                    "fs": fs,
                    "fields": "f2,f3,f4,f12,f14,f104,f105,f128",
                    "fltt": "2",
                },
                timeout=10,
            )
            rows = (data.get("data") or {}).get("diff") or []
            result = []
            for r in rows:
                result.append(SectorData(
                    name=r.get("f14", ""),
                    code=r.get("f12", ""),
                    avg_pct=_safe_float(r.get("f3")) or 0,
                    up_ratio=_safe_float(r.get("f104")) or 0,
                    leader=r.get("f128", ""),
                    leader_pct=_safe_float(r.get("f105")) or 0,
                ))
            return result
        except Exception as e:
            logger.warning("板块排名失败: %s", e)
            return []


def _safe_float(v) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
