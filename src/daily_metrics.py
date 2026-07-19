"""Deterministic derivation of daily price-volume evidence."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import math
from typing import Any, Mapping, Sequence


LEGACY_KEYS = (
    "volume_ratio_5d",
    "volume_change_vs_prev",
    "amount_change_vs_prev",
    "amplitude",
    "close_position",
)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _rounded(value: Any) -> float | None:
    parsed = _number(value)
    return round(parsed, 2) if parsed is not None else None


def _ratio(numerator: Any, denominator: Any) -> float | None:
    numerator_value = _number(numerator)
    denominator_value = _number(denominator)
    if numerator_value is None or denominator_value in (None, 0):
        return None
    return round(numerator_value / denominator_value, 2)


def _change(current: Any, previous: Any) -> float | None:
    ratio = _ratio(current, previous)
    return round(ratio - 1, 2) if ratio is not None else None


def _mean(values: Sequence[Any]) -> float | None:
    parsed = [_number(value) for value in values]
    if not parsed or any(value is None for value in parsed):
        return None
    return sum(value for value in parsed if value is not None) / len(parsed)


def _row_date(row: Mapping[str, Any]) -> date | None:
    value = row.get("date")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _legacy_metrics(bars: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
    result = dict.fromkeys(LEGACY_KEYS)
    if len(bars) < 2:
        return result

    latest = bars[-1]
    previous = bars[-2]
    result["volume_change_vs_prev"] = _change(
        latest.get("volume"), previous.get("volume")
    )
    result["amount_change_vs_prev"] = _change(
        latest.get("amount"), previous.get("amount")
    )
    result["amplitude"] = _ratio(
        (
            high - low
            if (high := _number(latest.get("high"))) is not None
            and (low := _number(latest.get("low"))) is not None
            else None
        ),
        previous.get("close"),
    )
    result["close_position"] = _ratio(
        (
            close - low
            if (close := _number(latest.get("close"))) is not None
            and (low := _number(latest.get("low"))) is not None
            else None
        ),
        (
            high - low
            if (high := _number(latest.get("high"))) is not None
            and (low := _number(latest.get("low"))) is not None
            else None
        ),
    )
    if len(bars) >= 6:
        result["volume_ratio_5d"] = _ratio(
            latest.get("volume"),
            _mean([row.get("volume") for row in bars[-6:-1]]),
        )
    return result


def _windowed_bars(
    bars: Sequence[Mapping[str, Any]], window_days: int
) -> list[Mapping[str, Any]]:
    if not bars:
        return []
    latest_date = _row_date(bars[-1])
    if latest_date is None or isinstance(window_days, bool) or window_days <= 0:
        return list(bars)
    start = latest_date - timedelta(days=window_days - 1)
    return [
        row
        for row in bars
        if (row_date := _row_date(row)) is not None and start <= row_date <= latest_date
    ]


def _volume_vs_average(
    bars: Sequence[Mapping[str, Any]], count: int
) -> float | None:
    if len(bars) < count:
        return None
    volumes = [row.get("volume") for row in bars[-count:]]
    return _ratio(volumes[-1], _mean(volumes))


def _obv_direction(series: Any) -> str:
    if not isinstance(series, (list, tuple)) or len(series) < 21:
        return "unavailable"
    start = _number(series[-21])
    end = _number(series[-1])
    if start is None or end is None:
        return "unavailable"
    if end > start:
        return "rising"
    if end < start:
        return "falling"
    return "flat"


def _price_volume_label(
    price_change_pct: float | None, volume_state: str
) -> str:
    if price_change_pct is None or price_change_pct == 0 or volume_state == "normal":
        return "正常量能/量价中性"
    if volume_state == "unavailable":
        return "正常量能/量价中性"
    if price_change_pct > 0:
        return "放量上涨" if volume_state == "expanding" else "缩量上涨"
    return "放量下跌" if volume_state == "expanding" else "缩量下跌"


def derive_daily_metrics(
    bars: Sequence[Mapping[str, Any]],
    *,
    indicators: Mapping[str, Any] | None = None,
    quote: Mapping[str, Any] | None = None,
    window_days: int = 90,
) -> dict[str, Any]:
    """Return JSON-safe, nullable daily price-volume metrics."""
    indicators = indicators or {}
    quote = quote or {}
    valid_bars = [row for row in bars if isinstance(row, Mapping)]
    result: dict[str, Any] = _legacy_metrics(valid_bars)
    window = _windowed_bars(valid_bars, window_days)

    price_change_pct = None
    if len(window) >= 2:
        latest_close = _number(window[-1].get("close"))
        previous_close = _number(window[-2].get("close"))
        if latest_close is not None and previous_close not in (None, 0):
            price_change_pct = round(
                (latest_close / previous_close - 1) * 100,
                2,
            )

    volume_vs_ma5 = _volume_vs_average(window, 5)
    volume_vs_ma20 = _volume_vs_average(window, 20)
    recent20_vs_previous20 = None
    if len(window) >= 40:
        recent20_vs_previous20 = _ratio(
            _mean([row.get("volume") for row in window[-20:]]),
            _mean([row.get("volume") for row in window[-40:-20]]),
        )

    up_volumes: list[float] = []
    down_volumes: list[float] = []
    for previous, current in zip(window, window[1:]):
        previous_close = _number(previous.get("close"))
        current_close = _number(current.get("close"))
        volume = _number(current.get("volume"))
        if previous_close is None or current_close is None or volume is None:
            continue
        if current_close > previous_close:
            up_volumes.append(volume)
        elif current_close < previous_close:
            down_volumes.append(volume)
    up_down_ratio = (
        _ratio(_mean(up_volumes), _mean(down_volumes))
        if up_volumes and down_volumes
        else None
    )

    if volume_vs_ma20 is None:
        volume_state = "unavailable"
    elif volume_vs_ma20 >= 1.20:
        volume_state = "expanding"
    elif volume_vs_ma20 <= 0.80:
        volume_state = "contracting"
    else:
        volume_state = "normal"

    mfi14 = _rounded(indicators.get("mfi14"))
    cmf20 = _rounded(indicators.get("cmf20"))
    obv_direction = _obv_direction(indicators.get("obv_series"))
    flags: list[str] = []
    if (
        volume_vs_ma5 is not None
        and volume_vs_ma5 >= 1.20
        and recent20_vs_previous20 is not None
        and recent20_vs_previous20 <= 0.80
    ):
        flags.append("local_expansion_medium_contraction")
    if (
        price_change_pct is not None
        and price_change_pct > 0
        and volume_state == "expanding"
        and ((cmf20 is not None and cmf20 > 0) or obv_direction == "rising")
    ):
        flags.append("positive_flow_confirmation")
    if (
        price_change_pct is not None
        and price_change_pct < 0
        and volume_state == "expanding"
        and ((cmf20 is not None and cmf20 < 0) or obv_direction == "falling")
    ):
        flags.append("negative_flow_confirmation")

    gaps: list[str] = []
    if len(window) < 2 or price_change_pct is None:
        gaps.append("price_change_unavailable")
    if len(window) < 5:
        gaps.append("history_lt_5")
    if len(window) < 20:
        gaps.append("history_lt_20")
    if len(window) < 40:
        gaps.append("history_lt_40")
    if up_down_ratio is None:
        gaps.append("up_down_volume_ratio_unavailable")
    if obv_direction == "unavailable":
        gaps.append("obv_20d_unavailable")

    result.update(
        {
            "price_change_pct": price_change_pct,
            "intraday_volume_ratio": _rounded(quote.get("volume_ratio")),
            "volume_vs_ma5": volume_vs_ma5,
            "volume_vs_ma20": volume_vs_ma20,
            "recent20_vs_previous20": recent20_vs_previous20,
            "up_down_volume_ratio_90d": up_down_ratio,
            "mfi14": mfi14,
            "cmf20": cmf20,
            "obv_20d_direction": obv_direction,
            "turnover_rate": _rounded(quote.get("turnover_rate")),
            "volume_state": volume_state,
            "price_volume_label": _price_volume_label(
                price_change_pct, volume_state
            ),
            "interpretation_flags": flags,
            "evidence_gaps": gaps,
        }
    )
    return result
