"""Deterministic, side-effect-free workflow gate evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from typing import Any, Callable, Mapping

from .models import ArtifactSpec, GateSpec, SpecRegistry


@dataclass(frozen=True)
class GateResult:
    rule_id: str
    severity: str
    passed: bool
    expected: str
    actual: str
    remediation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class CheckReport:
    workflow: str
    phase: str
    results: tuple[GateResult, ...]

    @property
    def ok(self) -> bool:
        return not any(not item.passed and item.severity == "block" for item in self.results)

    def to_dict(self) -> dict[str, object]:
        return {"workflow": self.workflow, "phase": self.phase, "ok": self.ok,
                "results": [item.to_dict() for item in self.results]}


@dataclass(frozen=True)
class _Context:
    workflow: str
    phase: str
    registry: SpecRegistry
    root: Path
    now: datetime
    facts: Mapping[str, Any]


def _fact(ctx: _Context, gate: GateSpec) -> Any:
    gates = ctx.facts.get("gates", {})
    if isinstance(gates, Mapping) and gate.id in gates:
        return gates[gate.id]
    return ctx.facts.get(gate.check, ctx.facts.get(gate.id))


def _boolean(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    passed = bool(value)
    return passed, "truthy runtime fact", json.dumps(value, ensure_ascii=False, default=str)


def _path_exists(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    raw = value.get("path") if isinstance(value, Mapping) else value
    path = ctx.root / str(raw or "")
    passed = bool(raw) and path.exists()
    return passed, "existing path", str(path) if raw else "missing path fact"


def _json_field(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if not isinstance(value, Mapping):
        return False, "JSON field equals expected value", "missing mapping fact"
    try:
        payload = json.loads((ctx.root / str(value["path"])).read_text())
        actual: Any = payload
        for part in str(value["field"]).split("."):
            actual = actual[int(part)] if isinstance(actual, list) else actual[part]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        return False, str(value.get("expected", "present")), f"unavailable: {exc}"
    expected = value.get("expected", True)
    return actual == expected, json.dumps(expected, ensure_ascii=False), json.dumps(actual, ensure_ascii=False, default=str)


def _format_path(artifact: ArtifactSpec, ctx: _Context) -> Path:
    values = {"date": ctx.now.date().isoformat(), "week": ctx.now.strftime("%G-W%V")}
    params = ctx.facts.get("params", {})
    if isinstance(params, Mapping):
        values.update({str(k): str(v) for k, v in params.items()})
    try:
        raw = artifact.path.format_map(values)
    except KeyError:
        raw = artifact.path
    return ctx.root / raw


def _sqlite_artifact(artifact: ArtifactSpec, path: Path, ctx: _Context) -> tuple[bool, str]:
    if not path.is_file():
        return False, "database missing"
    table, column = ("stock_daily", "date") if artifact.kind == "bars" else ("stock_snapshots", "updated_at")
    where, args = ("", []) if artifact.kind == "bars" else (" where kind = ?", [artifact.kind])
    codes = ctx.facts.get("codes")
    if codes and isinstance(codes, list):
        marks = ",".join("?" for _ in codes)
        where += (" and" if where else " where") + f" code in ({marks})"
        args.extend(str(code) for code in codes)
    try:
        with sqlite3.connect(path) as connection:
            row = connection.execute(f"select max({column}) from {table}{where}", args).fetchone()
    except sqlite3.Error as exc:
        return False, f"snapshot unavailable: {exc}"
    return bool(row and row[0]), str(row[0]) if row and row[0] else f"no {artifact.kind} record"


def _is_current(artifact: ArtifactSpec, timestamp: str, ctx: _Context) -> bool:
    if artifact.freshness not in {"daily", "trading_day", "current_search", "report_publish"}:
        return True
    try:
        return date.fromisoformat(timestamp[:10]) == ctx.now.date()
    except ValueError:
        return False


def _artifact_result(artifact: ArtifactSpec, ctx: _Context) -> tuple[bool, str, str]:
    path = _format_path(artifact, ctx)
    if artifact.storage == "sqlite_data_access":
        exists, actual = _sqlite_artifact(artifact, path, ctx)
        passed = exists and _is_current(artifact, actual, ctx)
    else:
        exists = path.exists()
        actual = (datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
                  if exists else "missing")
        passed = exists and _is_current(artifact, actual, ctx)
    return passed, f"{artifact.id} exists and freshness={artifact.freshness}", actual


def _artifact_freshness(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    workflow = ctx.registry.workflows[ctx.workflow]
    ids = workflow.inputs if ctx.phase == "preflight" else workflow.outputs
    checks = [_artifact_result(ctx.registry.artifacts[item], ctx) for item in ids if item in ctx.registry.artifacts]
    failed = [actual for passed, _, actual in checks if not passed]
    return not failed, "all registered artifacts current", "; ".join(failed) if failed else "all current"


def _markdown_sections(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if not isinstance(value, Mapping): return False, "required markdown sections", "missing mapping fact"
    try: text = (ctx.root / str(value["path"])).read_text()
    except OSError as exc: return False, "required markdown sections", f"unavailable: {exc}"
    missing = [str(s) for s in value.get("sections", []) if str(s) not in text]
    return not missing, "all required markdown sections", "missing: " + ", ".join(missing) if missing else "all present"


def _source_links(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    text = json.dumps(value, ensure_ascii=False, default=str)
    links = sorted(set(re.findall(r"https?://[^\s\]\)\"']+", text)))
    return bool(links), "at least one traceable source URL", ", ".join(links) if links else "no source URL"


def _git_commit_contains(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if isinstance(value, bool):
        return _boolean(gate, ctx)
    if not isinstance(value, Mapping) or not value.get("path"):
        return False, "committed path and optional content", "missing path fact"
    target = f"{value.get('ref', 'HEAD')}:{value['path']}"
    run = subprocess.run(
        ["git", "show", target], cwd=ctx.root, text=True, capture_output=True, check=False
    )
    needle = value.get("contains")
    passed = run.returncode == 0 and (needle is None or str(needle) in run.stdout)
    actual = target if passed else (run.stderr.strip() or f"content not found in {target}")
    return passed, target + (f" contains {needle}" if needle is not None else " exists"), actual


def _git_pushed(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if value is not None:
        return _boolean(gate, ctx)
    run = subprocess.run(
        ["git", "rev-list", "--count", "@{upstream}..HEAD"],
        cwd=ctx.root, text=True, capture_output=True, check=False,
    )
    actual = run.stdout.strip() if run.returncode == 0 else run.stderr.strip()
    passed = run.returncode == 0 and actual == "0"
    return passed, "zero unpushed commits", actual or "unavailable"


def _generated_docs_clean(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if value is not None: return _boolean(gate, ctx)
    run = subprocess.run(["git", "diff", "--exit-code", "--", "AGENTS.md", "references"], cwd=ctx.root, capture_output=True)
    return run.returncode == 0, "generated documents unchanged", "clean" if run.returncode == 0 else "generated documents differ"


_EVALUATORS: dict[str, Callable[[GateSpec, _Context], tuple[bool, str, str]]] = {
    "path_exists": _path_exists, "json_field": _json_field,
    "artifact_freshness": _artifact_freshness, "markdown_sections": _markdown_sections,
    "source_links": _source_links,
    "git_commit_contains": _git_commit_contains,
    "git_pushed": _git_pushed,
    "generated_docs_clean": _generated_docs_clean,
}


def check_workflow(workflow_id: str, phase: str, registry: SpecRegistry, repo_root: Path,
                   now: datetime | None = None, facts: Mapping[str, Any] | None = None) -> CheckReport:
    if phase not in {"preflight", "completion"}: raise ValueError(f"unknown phase: {phase}")
    workflow = registry.workflows[workflow_id]
    ctx = _Context(workflow_id, phase, registry, Path(repo_root), now or datetime.now(), facts or {})
    entries = workflow.preflight if phase == "preflight" else workflow.completion
    results: list[GateResult] = []
    for entry in entries:
        if entry in registry.artifacts:
            artifact = registry.artifacts[entry]
            passed, expected, actual = _artifact_result(artifact, ctx)
            severity = "block" if artifact.missing == "block" else "warn"
            remediation = f"Run workflow {artifact.producer}"
        else:
            gate = registry.gates[entry]
            evaluator = _EVALUATORS.get(gate.check)
            if evaluator is None:
                passed, expected, actual = False, "registered evaluator", f"unknown evaluator: {gate.check}"
                severity = "block"
            else:
                passed, expected, actual = evaluator(gate, ctx)
                severity = gate.severity
            remediation = gate.remediation
        results.append(GateResult(entry, severity, passed, expected, actual, remediation))
    return CheckReport(workflow_id, phase, tuple(results))
