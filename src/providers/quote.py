"""行情 Provider: 腾讯→新浪→东财降级链。"""
from __future__ import annotations

import re
import time
import logging
from typing import Optional

from .http_client import get_text, get_json
from .models import QuoteData, EvidenceMeta, tencent_a_code, sina_code, em_secid, detect_market

logger = logging.getLogger(__name__)


class QuoteProvider:
    """实时行情，腾讯→新浪→东财逐级降级。"""

    def get_realtime(self, code: str) -> QuoteData:
        """获取单只股票行情。"""
        result = self._try_tencent(code)
        if result:
            return result
        result = self._try_sina(code)
        if result:
            return result
        return self._try_eastmoney(code) or QuoteData(
            symbol=code, name="", source_chain=["tencent:fail", "sina:fail", "eastmoney:fail"])

    def get_batch(self, codes: list[str]) -> dict[str, QuoteData]:
        """批量获取行情。一次腾讯请求拉全部，失败逐个降级。"""
        results = {}
        # 批量腾讯
        tc_codes = [tencent_a_code(c) for c in codes]
        try:
            joined = ",".join(tc_codes)
            text, _ = get_text(f"https://qt.gtimg.cn/q={joined}", encoding="gbk", timeout=8)
            for tc in tc_codes:
                m = re.search(rf'v_{re.escape(tc)}="(.*?)"', text)
                if m:
                    results[tc] = _parse_tencent_quote(tc, m.group(1))
        except Exception as e:
            logger.warning("腾讯批量行情失败: %s", e)

        # 逐个补充
        for i, code in enumerate(codes):
            tc = tc_codes[i]
            if tc in results and results[tc] and results[tc].price > 0:
                continue
            results[tc] = self.get_realtime(code)

        # 用原始 code 做 key
        return {codes[i]: results.get(tc_codes[i], QuoteData(symbol=codes[i]))
                for i in range(len(codes))}

    def _try_tencent(self, code: str) -> Optional[QuoteData]:
        tc = tencent_a_code(code)
        try:
            text, _ = get_text(f"https://qt.gtimg.cn/q={tc}", encoding="gbk", timeout=8)
            m = re.search(rf'v_{re.escape(tc)}="(.*?)"', text)
            if m:
                q = _parse_tencent_quote(tc, m.group(1))
                if q and q.price > 0:
                    q.source = "tencent"
                    q.source_chain = ["tencent:ok"]
                    return q
        except Exception as e:
            logger.debug("腾讯行情 %s 失败: %s", code, e)
        return None

    def _try_sina(self, code: str) -> Optional[QuoteData]:
        sc = sina_code(code)
        try:
            text, _ = get_text(f"https://hq.sinajs.cn/list={sc}", encoding="gbk",
                               headers={"Referer": "https://finance.sina.com.cn/"}, timeout=8)
            m = re.search(rf'hq_str_{re.escape(sc)}="(.*?)"', text)
            if m:
                q = _parse_sina_quote(code, sc, m.group(1))
                if q and q.price > 0:
                    q.source = "sina"
                    q.source_chain = ["tencent:fail", "sina:ok"]
                    return q
        except Exception as e:
            logger.debug("新浪行情 %s 失败: %s", code, e)
        return None

    def _try_eastmoney(self, code: str) -> Optional[QuoteData]:
        try:
            secid = em_secid(code)
            data = get_json(
                "https://push2.eastmoney.com/api/qt/stock/get",
                params={"secid": secid, "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f60,f169,f170,f162,f167"},
                timeout=8,
            )
            d = (data.get("data") or {})
            if not d or not d.get("f58"):
                return None
            market = detect_market(code)
            q = QuoteData(
                symbol=code, name=d.get("f58", ""), market=market,
                price=float(d.get("f43", 0)),
                prev_close=float(d.get("f60", 0)),
                open=float(d.get("f46", 0)),
                high=float(d.get("f44", 0)),
                low=float(d.get("f45", 0)),
                volume=float(d.get("f47", 0)),
                amount=float(d.get("f48", 0)),
                pe=_safe_float(d.get("f162")),
                pb=_safe_float(d.get("f167")),
                change_pct=float(d.get("f170", 0)),
                change=float(d.get("f169", 0)),
                currency="CNY" if market != "HK" else "HKD",
                source="eastmoney",
                source_chain=["tencent:fail", "sina:fail", "eastmoney:ok"],
            )
            return q
        except Exception as e:
            logger.debug("东财行情 %s 失败: %s", code, e)
        return None


def _parse_tencent_quote(tc_code: str, raw: str) -> Optional[QuoteData]:
    """解析腾讯 qt.gtimg.cn 返回的 ~ 分隔字段。"""
    f = raw.split("~")
    if len(f) < 40:
        return None
    try:
        market = ""
        if tc_code.startswith("sh"):
            market = "SH"
        elif tc_code.startswith("sz"):
            market = "SZ"
        elif tc_code.startswith("hk"):
            market = "HK"
        elif tc_code.startswith("bj"):
            market = "BJ"

        return QuoteData(
            symbol=tc_code.replace("sh", "").replace("sz", "").replace("hk", "").replace("bj", "").upper(),
            name=f[1],
            market=market,
            price=_safe_float(f[3]),
            prev_close=_safe_float(f[4]) or 0,
            open=_safe_float(f[5]) or 0,
            high=_safe_float(f[33]) or 0,
            low=_safe_float(f[34]) or 0,
            change_pct=_safe_float(f[32]),
            volume=_safe_float(f[6]) or 0,
            amount=_safe_float(f[37]) or 0,
            turnover_rate=_safe_float(f[38]),
            pe=_safe_float(f[39]),
            pb=_safe_float(f[46]),
            market_cap=_safe_float(f[44]),
            high_52w=_safe_float(f[48]),
            low_52w=_safe_float(f[49]),
            ytd=_safe_float(f[61]),
            currency="CNY" if not tc_code.startswith("hk") else "HKD",
        )
    except Exception:
        return None


def _parse_sina_quote(code: str, sc: str, raw: str) -> Optional[QuoteData]:
    """解析新浪 hq.sinajs.cn 返回的逗号分隔字段。"""
    f = raw.split(",")
    if len(f) < 30:
        return None
    try:
        market = detect_market(code)
        is_hk = sc.startswith("hk")
        # A-share format: name, open, prev_close, price, high, low, ...
        # HK format: name, open, prev_close, high, low, price, ...
        if is_hk:
            return QuoteData(
                symbol=code, name=f[1], market=market,
                price=_safe_float(f[6]) or 0,
                prev_close=_safe_float(f[3]) or 0,
                open=_safe_float(f[2]) or 0,
                high=_safe_float(f[4]) or 0,
                low=_safe_float(f[5]) or 0,
                volume=_safe_float(f[8]) or 0,
                amount=_safe_float(f[9]) or 0,
                pe=_safe_float(f[17]),
                currency="HKD",
            )
        else:
            return QuoteData(
                symbol=code, name=f[0], market=market,
                price=_safe_float(f[3]) or 0,
                prev_close=_safe_float(f[2]) or 0,
                open=_safe_float(f[1]) or 0,
                high=_safe_float(f[4]) or 0,
                low=_safe_float(f[5]) or 0,
                volume=_safe_float(f[8]) or 0,
                amount=_safe_float(f[9]) or 0,
                pe=_safe_float(f[39]),
                pb=_safe_float(f[41]),
                currency="CNY",
            )
    except Exception:
        return None


def _safe_float(v) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None
