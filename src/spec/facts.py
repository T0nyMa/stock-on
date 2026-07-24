"""Durable, workflow-scoped facts used by specification gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def merge_facts(
    base: Mapping[str, Any], override: Mapping[str, Any]
) -> dict[str, Any]:
    """Recursively merge explicit facts over durable facts."""
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(value, Mapping) and isinstance(existing, Mapping):
            merged[key] = merge_facts(existing, value)
        else:
            merged[key] = value
    return merged


def load_workflow_facts(repo_root: Path, workflow: str) -> dict[str, Any]:
    """Load a workflow's durable facts, returning empty facts when absent."""
    path = Path(repo_root) / "data/spec/workflow-facts" / f"{workflow}.json"
    if not path.exists():
        return {}
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, Mapping):
        raise ValueError(f"{path}: workflow facts record must be a JSON object")
    facts = record.get("facts")
    if not isinstance(facts, Mapping):
        raise ValueError(f"{path}: facts must be a JSON object")
    return dict(facts)
