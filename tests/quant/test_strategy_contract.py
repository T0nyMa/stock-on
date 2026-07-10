import pytest

from src.quant.strategy import StrategyResult


def test_actionable_strategy_requires_invalidation_and_target():
    with pytest.raises(ValueError, match="invalidation"):
        StrategyResult("breakout", "buy", 70, 0.8, "trend", (5, 10), (10, 11))


def test_strategy_contract_computes_risk_reward_and_serializes_calibration():
    result = StrategyResult(
        strategy="breakout", signal="buy", score=70, confidence=0.8,
        setup_type="trend", horizon_days=(5, 10), entry_zone=(10, 11),
        invalidation=9, targets=(14,), calibration={"status": "available", "sample_size": 40},
    ).to_dict()

    assert result["risk_reward"] == 2.33
    assert result["calibration"]["sample_size"] == 40


def test_non_actionable_strategy_may_lack_levels_but_bounds_are_validated():
    assert StrategyResult("trend", "hold", 50, 0.5, "none", (5,), None).to_dict()["risk_reward"] is None
    with pytest.raises(ValueError, match="score"):
        StrategyResult("trend", "hold", 101, 0.5, "none", (5,), None)
