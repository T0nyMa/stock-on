# -*- coding: utf-8 -*-
"""
===================================
TickFlowDailyFetcher - TickFlow 免费日K线数据源 (Priority 0)
===================================

数据来源：TickFlow 自有服务器集群（非爬虫）
特点：免费、无需注册、稳定
覆盖：A 股（沪/深/北）

使用 TickFlow.free() 免费套餐，提供历史日K线和标的信息。
"""

import logging
from datetime import datetime as dt
from typing import List, Optional

import pandas as pd

from .base import (
    BaseFetcher,
    DataFetchError,
    STANDARD_COLUMNS,
    is_bse_code,
    normalize_stock_code,
    _is_hk_market,
    _is_us_market,
)

logger = logging.getLogger(__name__)


def _to_tickflow_symbol(stock_code: str) -> Optional[str]:
    """将系统内部代码转换为 TickFlow 格式 (600519.SH / 000001.SZ / 920662.BJ)"""
    code = normalize_stock_code(stock_code)
    if not code.isdigit() or len(code) != 6:
        return None
    if code.startswith(('60', '68')):
        return f"{code}.SH"
    if code.startswith('92'):
        return f"{code}.BJ"
    return f"{code}.SZ"


def _from_tickflow_symbol(symbol: str) -> str:
    """从 TickFlow 格式提取纯代码"""
    return symbol.split(".")[0] if "." in symbol else symbol


def _date_to_timestamp_ms(date_str: str) -> int:
    """将 YYYY-MM-DD 转为毫秒时间戳 (TickFlow API 参数格式)"""
    d = dt.strptime(date_str, "%Y-%m-%d")
    return int(d.timestamp() * 1000)


class TickFlowDailyFetcher(BaseFetcher):
    """TickFlow 免费日K线数据源 (A 股首选)"""

    name = "TickFlowDailyFetcher"
    priority = 0

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = None

    def _get_client(self):
        if self._client is None:
            from tickflow import TickFlow
            self._client = TickFlow.free()
        return self._client

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def is_available_for_request(self, capability: str = "") -> bool:
        """免费套餐始终可用，无凭证要求"""
        return True

    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        symbol = _to_tickflow_symbol(stock_code)
        if symbol is None:
            raise DataFetchError(
                f"TickFlowDailyFetcher 不支持 {stock_code}，仅支持A股(沪/深/北)"
            )

        client = self._get_client()
        start_ms = _date_to_timestamp_ms(start_date)
        end_ms = _date_to_timestamp_ms(end_date)

        try:
            df = client.klines.get(
                symbol,
                period="1d",
                start_time=start_ms,
                end_time=end_ms,
                adjust="forward",
                as_dataframe=True,
            )
        except Exception as e:
            raise DataFetchError(
                f"TickFlow 获取 {symbol} 日K线失败: {e}"
            ) from e

        if df is None or len(df) == 0:
            raise DataFetchError(f"TickFlow 未查询到 {symbol} 的数据")

        return df

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        df = df.copy()

        col_map = {
            "trade_date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "amount": "amount",
        }
        df = df.rename(columns=col_map)

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        if "pct_chg" not in df.columns and "close" in df.columns:
            df["pct_chg"] = df["close"].pct_change() * 100
            df["pct_chg"] = df["pct_chg"].fillna(0).round(2)

        df["code"] = stock_code

        keep_cols = ["code", "date", "open", "high", "low", "close", "volume", "amount", "pct_chg"]
        existing = [c for c in keep_cols if c in df.columns]
        df = df[existing]

        return df

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        """从 TickFlow 获取股票名称"""
        if _is_hk_market(stock_code) or _is_us_market(stock_code):
            return None

        symbol = _to_tickflow_symbol(stock_code)
        if symbol is None:
            return None

        try:
            client = self._get_client()
            instruments = client.instruments.batch(symbols=[symbol])
            if instruments:
                return instruments[0].get("name") or None
        except Exception as e:
            logger.debug("TickFlow 获取股票名称失败 %s: %s", stock_code, e)

        return None
