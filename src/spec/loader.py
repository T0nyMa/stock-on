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
ARTIFACT_STORAGE = {"filesystem", "sqlite_database", "sqlite_data_access"}
ARTIFACT_FRESHNESS = {"daily", "trading_day", "current_search", "report_publish", "latest_disclosure", "thesis_change", "weekly", "change", "current", "incremental"}


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


def _schema(record, required, optional, source):
    _required(record, required, source)
    unknown = sorted(set(record) - set(required) - set(optional))
    if unknown:
        raise SpecLoadError(f"unknown key: {unknown[0]} in {source}")


def _string(record, key, source, optional=False):
    value = record.get(key)
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SpecLoadError(f"expected non-empty string for {key} in {source}")
    return value


def _integer(record, key, source):
    value = record.get(key)
    if type(value) is not int:
        raise SpecLoadError(f"expected integer for {key} in {source}")
    return value


def _tuple(record: dict[str, Any], key: str, source: Path) -> tuple[str, ...]:
    value = record[key]
    if not isinstance(value, (list, tuple)):
        raise SpecLoadError(f"expected list for {key} in {source}")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise SpecLoadError(f"expected string element for {key} in {source}")
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
        _schema(record, ("id", "intents", "workflow", "priority"), ("skill",), path)
        routes.append(
            RouteSpec(
                id=_string(record, "id", path),
                intents=_tuple(record, "intents", path),
                workflow=_string(record, "workflow", path),
                skill=_string(record, "skill", path, optional=True),
                priority=_integer(record, "priority", path),
            )
        )
    return _index(routes, lambda route: route.id)


def _load_artifacts(path: Path) -> dict[str, ArtifactSpec]:
    artifacts = []
    keys = ("id", "path", "producer", "consumers", "freshness", "missing")
    for record in _records(_read_yaml(path), path):
        _schema(record, keys, ("storage", "kind"), path)
        missing = _string(record, "missing", path)
        if missing not in {"block", "unavailable"}: raise SpecLoadError(f"unknown missing behavior: {missing}")
        storage = _string(record, "storage", path) if "storage" in record else "filesystem"
        freshness = _string(record, "freshness", path)
        if storage not in ARTIFACT_STORAGE: raise SpecLoadError(f"unknown artifact storage: {storage}")
        if freshness not in ARTIFACT_FRESHNESS: raise SpecLoadError(f"unknown artifact freshness: {freshness}")
        artifacts.append(
            ArtifactSpec(
                id=_string(record, "id", path), path=_string(record, "path", path),
                producer=_string(record, "producer", path),
                consumers=_tuple(record, "consumers", path),
                freshness=freshness, missing=missing, storage=storage,
                kind=_string(record, "kind", path, optional=True),
            )
        )
    return _index(artifacts, lambda artifact: artifact.id)


def _load_skills(path: Path) -> dict[str, SkillSpec]:
    skills = []
    keys = ("id", "path", "category", "workflows", "excludes")
    for record in _records(_read_yaml(path), path):
        _schema(record, keys, (), path)
        skills.append(
            SkillSpec(
                id=_string(record, "id", path), path=_string(record, "path", path),
                category=_string(record, "category", path),
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
            _schema(record, ("id", "description", "gates"), (), path)
            policy_gates = []
            for gate_record in _records(record["gates"], path):
                _schema(gate_record, gate_keys, (), path)
                for key in gate_keys: _string(gate_record, key, path)
                severity = gate_record["severity"]
                if severity not in {"block", "warn", "info"}:
                    raise SpecLoadError(f"unknown gate severity: {severity}")
                gate = GateSpec(**{key: gate_record[key] for key in gate_keys})
                policy_gates.append(gate)
                gates.append(gate)
            policies.append(
                PolicySpec(
                    id=_string(record, "id", path), description=_string(record, "description", path),
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
        "optional_inputs",
        "outputs",
        "policies",
        "skills",
        "steps",
        "preflight",
        "completion",
        "on_failure",
    )
    for path in sorted(directory.glob("*.yaml")):
        for record in _records(_read_yaml(path), path):
            _schema(record, ("id", *tuple_keys), (), path)
            workflows.append(
                WorkflowSpec(
                    id=_string(record, "id", path),
                    **{key: _tuple(record, key, path) for key in tuple_keys},
                )
            )
    return _index(workflows, lambda workflow: workflow.id)


def load_registry(root: Path) -> SpecRegistry:
    """Load the YAML registries rooted at *root* into immutable typed records."""
    root = Path(root)
    project_path = root / "project.yaml"
    project = _mapping(_read_yaml(project_path), project_path)
    _schema(project, ("schema_version", "project"), ("timezone", "principles", "runtime", "ownership"), project_path)
    _string(project, "schema_version", project_path); _string(project, "project", project_path)
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
