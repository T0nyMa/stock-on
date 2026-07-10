"""Validated, comparable strategy-result contract."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .models import json_safe


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    signal: str
    score: int
    confidence: float
    setup_type: str
    horizon_days: tuple[int, ...]
    entry_zone: tuple[float, float] | None
    invalidation: float | None = None
    targets: tuple[float, ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()
    risk_flags: tuple[str, ...] = ()
    calibration: dict[str, Any] = field(default_factory=lambda: {"status": "unavailable"})

    def __post_init__(self):
        if self.signal not in {"buy", "hold", "sell"}:
            raise ValueError("signal must be buy, hold, or sell")
        if not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if self.signal in {"buy", "sell"} and self.invalidation is None:
            raise ValueError("actionable signal requires invalidation")
        if self.signal in {"buy", "sell"} and not self.targets:
            raise ValueError("actionable signal requires targets")

    def to_dict(self):
        rr = None
        if self.entry_zone and self.invalidation is not None and self.targets:
            entry = sum(self.entry_zone) / 2
            risk = abs(entry - self.invalidation)
            reward = abs(self.targets[0] - entry)
            rr = round(reward / risk, 2) if risk else None
        return json_safe({
            "strategy": self.strategy, "signal": self.signal, "score": self.score,
            "confidence": self.confidence, "setup_type": self.setup_type,
            "horizon_days": self.horizon_days, "entry_zone": self.entry_zone,
            "invalidation": self.invalidation, "targets": self.targets,
            "risk_reward": rr, "evidence": self.evidence,
            "risk_flags": self.risk_flags, "calibration": self.calibration,
        })
