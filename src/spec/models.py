from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GateSpec:
    id: str
    severity: str
    check: str
    message: str
    remediation: str


@dataclass(frozen=True)
class RouteSpec:
    id: str
    intents: tuple[str, ...]
    workflow: str
    skill: str | None
    priority: int


@dataclass(frozen=True)
class ArtifactSpec:
    id: str
    path: str
    producer: str
    consumers: tuple[str, ...]
    freshness: str
    missing: str


@dataclass(frozen=True)
class SkillSpec:
    id: str
    path: str
    category: str
    workflows: tuple[str, ...]
    excludes: tuple[str, ...]


@dataclass(frozen=True)
class PolicySpec:
    id: str
    description: str
    gates: tuple[GateSpec, ...]


@dataclass(frozen=True)
class WorkflowSpec:
    id: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    policies: tuple[str, ...]
    skills: tuple[str, ...]
    steps: tuple[str, ...]
    preflight: tuple[str, ...]
    completion: tuple[str, ...]


@dataclass(frozen=True)
class SpecRegistry:
    root: Path
    project: dict[str, Any]
    routes: dict[str, RouteSpec]
    artifacts: dict[str, ArtifactSpec]
    skills: dict[str, SkillSpec]
    policies: dict[str, PolicySpec]
    workflows: dict[str, WorkflowSpec]
    gates: dict[str, GateSpec]
