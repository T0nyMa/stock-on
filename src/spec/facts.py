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
    expected_keys = {"schema_version", "workflow", "facts"}
    unknown = sorted(set(record) - expected_keys)
    missing = sorted(expected_keys - set(record))
    if unknown:
        raise ValueError(f"{path}: unknown top-level keys: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{path}: missing top-level keys: {', '.join(missing)}")
    if record["schema_version"] != "1.0":
        raise ValueError(f"{path}: unsupported schema_version: {record['schema_version']}")
    if record["workflow"] != workflow:
        raise ValueError(
            f"{path}: workflow mismatch: expected {workflow}, got {record['workflow']}"
        )
    facts = record.get("facts")
    if not isinstance(facts, Mapping):
        raise ValueError(f"{path}: facts must be a JSON object")
    positions = facts.get("positions")
    if positions is not None:
        if not isinstance(positions, list) or not positions:
            raise ValueError(f"{path}: positions must be a non-empty list")
        for index, position in enumerate(positions):
            if (
                not isinstance(position, Mapping)
                or set(position) != {"code", "name"}
                or any(
                    not isinstance(position.get(key), str)
                    or not position[key].strip()
                    for key in ("code", "name")
                )
            ):
                raise ValueError(f"{path}: positions[{index}] must contain code and name")
    return dict(facts)
