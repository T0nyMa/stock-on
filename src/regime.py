"""Market regime detection from technical indicators."""

STRATEGY_MAP = {
    "trending_up": [
        "ma_golden_cross", "volume_breakout", "bull_trend",
        "shrink_pullback", "dragon_head",
    ],
    "volatile": [
        "chan_theory", "box_oscillation", "wave_theory",
        "bottom_volume", "one_yang_three_yin",
    ],
    "sector_hot": [
        "hot_theme", "event_driven", "emotion_cycle", "dragon_head",
    ],
    "bearish": [
        "expectation_repricing", "growth_quality", "event_driven",
    ],
}


def detect_regime(indicators: dict) -> dict:
    """Detect the current market regime from indicators dict and return
    the regime type with recommended strategies."""
    volume_ratio = indicators.get("volume", {}).get("volume_ratio", 0) or 0
    ma_alignment = indicators.get("trend", {}).get("ma_alignment", "")

    # sector_hot overrides everything
    if volume_ratio > 2.0:
        regime = "sector_hot"
    elif "MA5>MA10>MA20" in ma_alignment:
        regime = "trending_up"
    elif "MA5<MA10<MA20" in ma_alignment:
        regime = "bearish"
    else:
        regime = "volatile"

    return {
        "regime": regime,
        "strategies": STRATEGY_MAP[regime],
        "confidence": _regime_confidence(indicators, regime),
    }


def _regime_confidence(indicators: dict, regime: str) -> float:
    """Compute a rough confidence score for the detected regime (0.0 – 1.0)."""
    volume_ratio = indicators.get("volume", {}).get("volume_ratio", 0) or 0
    trend_strength = indicators.get("trend", {}).get("trend_strength", 0) or 0

    if regime == "sector_hot":
        return min(0.5 + volume_ratio * 0.15, 1.0)
    if regime == "bearish":
        return min(0.5 + abs(trend_strength) * 0.3, 1.0)
    if regime == "trending_up":
        return min(0.5 + trend_strength * 0.3, 1.0)
    return 0.3
