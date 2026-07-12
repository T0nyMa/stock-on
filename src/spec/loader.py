from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml

from .models import (
    ArtifactSpec,
    GateSpec,
    PolicySpec,
    RouteSpec,
    SkillSpec,
    SpecRegistry,
    WorkflowSpec,
)


class SpecLoadError(ValueError):
    """Raised when specification files cannot be loaded or validated."""


T = TypeVar("T")


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise SpecLoadError(f"failed to load {path}: {exc}") from exc


def _mapping(value: Any, source: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpecLoadError(f"expected mapping in {source}")
    return value


def _records(value: Any, source: Path) -> list[dict[str, Any]]:
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [_mapping(item, source) for item in values]


def _required(record: dict[str, Any], keys: tuple[str, ...], source: Path) -> None:
    missing = [key for key in keys if key not in record]
    if missing:
        raise SpecLoadError(f"missing required key: {missing[0]} in {source}")


def _tuple(record: dict[str, Any], key: str, source: Path) -> tuple[str, ...]:
    value = record[key]
    if not isinstance(value, (list, tuple)):
        raise SpecLoadError(f"expected list for {key} in {source}")
    return tuple(value)


def _index(records: list[T], get_id: Callable[[T], str]) -> dict[str, T]:
    result: dict[str, T] = {}
    for record in records:
        record_id = get_id(record)
        if record_id in result:
            raise SpecLoadError(f"duplicate id: {record_id}")
        result[record_id] = record
    return result


def _load_routes(path: Path) -> dict[str, RouteSpec]:
    routes = []
    for record in _records(_read_yaml(path), path):
        _required(record, ("id", "intents", "workflow", "priority"), path)
        routes.append(
            RouteSpec(
                id=record["id"],
                intents=_tuple(record, "intents", path),
                workflow=record["workflow"],
                skill=record.get("skill"),
                priority=record["priority"],
            )
        )
    return _index(routes, lambda route: route.id)


def _load_artifacts(path: Path) -> dict[str, ArtifactSpec]:
    artifacts = []
    keys = ("id", "path", "producer", "consumers", "freshness", "missing")
    for record in _records(_read_yaml(path), path):
        _required(record, keys, path)
        artifacts.append(
            ArtifactSpec(
                id=record["id"],
                path=record["path"],
                producer=record["producer"],
                consumers=_tuple(record, "consumers", path),
                freshness=record["freshness"],
                missing=record["missing"],
            )
        )
    return _index(artifacts, lambda artifact: artifact.id)


def _load_skills(path: Path) -> dict[str, SkillSpec]:
    skills = []
    keys = ("id", "path", "category", "workflows", "excludes")
    for record in _records(_read_yaml(path), path):
        _required(record, keys, path)
        skills.append(
            SkillSpec(
                id=record["id"],
                path=record["path"],
                category=record["category"],
                workflows=_tuple(record, "workflows", path),
                excludes=_tuple(record, "excludes", path),
            )
        )
    return _index(skills, lambda skill: skill.id)


def _load_policies(directory: Path) -> tuple[dict[str, PolicySpec], dict[str, GateSpec]]:
    policies: list[PolicySpec] = []
    gates: list[GateSpec] = []
    gate_keys = ("id", "severity", "check", "message", "remediation")
    for path in sorted(directory.glob("*.yaml")):
        for record in _records(_read_yaml(path), path):
            _required(record, ("id", "description", "gates"), path)
            policy_gates = []
            for gate_record in _records(record["gates"], path):
                _required(gate_record, gate_keys, path)
                severity = gate_record["severity"]
                if severity not in {"block", "warn", "info"}:
                    raise SpecLoadError(f"unknown gate severity: {severity}")
                gate = GateSpec(**{key: gate_record[key] for key in gate_keys})
                policy_gates.append(gate)
                gates.append(gate)
            policies.append(
                PolicySpec(
                    id=record["id"],
                    description=record["description"],
                    gates=tuple(policy_gates),
                )
            )
    return (
        _index(policies, lambda policy: policy.id),
        _index(gates, lambda gate: gate.id),
    )


def _load_workflows(directory: Path) -> dict[str, WorkflowSpec]:
    workflows = []
    tuple_keys = (
        "inputs",
        "outputs",
        "policies",
        "skills",
        "steps",
        "preflight",
        "completion",
    )
    for path in sorted(directory.glob("*.yaml")):
        for record in _records(_read_yaml(path), path):
            _required(record, ("id", *tuple_keys), path)
            workflows.append(
                WorkflowSpec(
                    id=record["id"],
                    **{key: _tuple(record, key, path) for key in tuple_keys},
                )
            )
    return _index(workflows, lambda workflow: workflow.id)


def load_registry(root: Path) -> SpecRegistry:
    """Load the YAML registries rooted at *root* into immutable typed records."""
    root = Path(root)
    project_path = root / "project.yaml"
    project = _mapping(_read_yaml(project_path), project_path)
    _required(project, ("schema_version", "project"), project_path)
    policies, gates = _load_policies(root / "policies")
    return SpecRegistry(
        root=root,
        project=project,
        routes=_load_routes(root / "routes.yaml"),
        artifacts=_load_artifacts(root / "artifacts.yaml"),
        skills=_load_skills(root / "skills.yaml"),
        policies=policies,
        workflows=_load_workflows(root / "workflows"),
        gates=gates,
    )
