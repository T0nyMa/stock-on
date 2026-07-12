"""Deterministic, side-effect-free workflow gate evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from string import Formatter
import sqlite3
import subprocess
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    timezone: ZoneInfo


def _fact(ctx: _Context, gate: GateSpec) -> Any:
    gates = ctx.facts.get("gates", {})
    if isinstance(gates, Mapping) and gate.id in gates:
        return gates[gate.id]
    return ctx.facts.get(gate.check, ctx.facts.get(gate.id))


def _boolean(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if type(value) is not bool:
        return False, "JSON boolean", f"invalid boolean fact: {type(value).__name__}"
    return value, "true", json.dumps(value)


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


def _format_path(artifact: ArtifactSpec, ctx: _Context, extra: Mapping[str, Any] | None = None) -> Path:
    values = {"date": ctx.now.date().isoformat(), "week": ctx.now.strftime("%G-W%V")}
    params = ctx.facts.get("params", {})
    if isinstance(params, Mapping):
        values.update({str(k): str(v) for k, v in params.items()})
    if extra:
        values.update({str(k): str(v) for k, v in extra.items()})
    required = {field for _, field, _, _ in Formatter().parse(artifact.path) if field}
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError("unresolved template parameters: " + ", ".join(missing))
    raw = artifact.path.format_map(values)
    return ctx.root / raw


def _required_codes(ctx: _Context) -> list[str]:
    codes = ctx.facts.get("codes")
    if isinstance(codes, list):
        return list(dict.fromkeys(str(code) for code in codes))
    params = ctx.facts.get("params")
    if isinstance(params, Mapping) and params.get("code") is not None:
        return [str(params["code"])]
    return []


def _lookup_codes(code: str) -> list[str]:
    """Mirror MarketDataStore's public code-resolution semantics without writes."""
    value = str(code or "").strip().upper()
    if value.startswith("HK"):
        return [value]
    if value.isdigit() and len(value) == 5:
        return [value, f"HK{value}"]
    return [value]


def _sqlite_artifact(artifact: ArtifactSpec, path: Path, ctx: _Context) -> tuple[bool, str]:
    if not path.is_file():
        return False, "database missing"
    table, column = ("stock_daily", "date") if artifact.kind == "bars" else ("stock_snapshots", "updated_at")
    base_where, base_args = ("", []) if artifact.kind == "bars" else (" where kind = ?", [artifact.kind])
    codes = _required_codes(ctx)
    try:
        with sqlite3.connect(path) as connection:
            if codes:
                found: dict[str, str | None] = {}
                for code in codes:
                    candidates = _lookup_codes(code)
                    marks = ",".join("?" for _ in candidates)
                    where = base_where + (" and" if base_where else " where") + f" code in ({marks})"
                    row = connection.execute(
                        f"select max({column}) from {table}{where}", [*base_args, *candidates]
                    ).fetchone()
                    found[code] = str(row[0]) if row and row[0] else None
            else:
                row = connection.execute(
                    f"select max({column}) from {table}{base_where}", base_args
                ).fetchone()
                found = {"*": str(row[0]) if row and row[0] else None}
    except sqlite3.Error as exc:
        return False, f"snapshot unavailable: {exc}"
    failures = {
        code: timestamp for code, timestamp in found.items()
        if timestamp is None or not _is_current(artifact, timestamp, ctx)
    }
    actual = ", ".join(
        f"{code}={timestamp or 'missing'}" for code, timestamp in sorted(found.items())
    )
    return not failures, actual


def _is_current(artifact: ArtifactSpec, timestamp: str, ctx: _Context) -> bool:
    if artifact.freshness in {"current", "incremental"}:
        return True
    if artifact.freshness in {"latest_disclosure", "thesis_change", "change"}:
        versions = ctx.facts.get("freshness", {})
        item = versions.get(artifact.id) if isinstance(versions, Mapping) else None
        return (
            isinstance(item, Mapping)
            and bool(item.get("current_version"))
            and item.get("current_version") == item.get("latest_version")
        )
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ctx.timezone)
        date = parsed.astimezone(ctx.timezone).date()
        today = ctx.now.astimezone(ctx.timezone).date()
        if artifact.freshness == "weekly":
            return date.isocalendar()[:2] == today.isocalendar()[:2]
        return date == today
    except ValueError:
        return False


def _artifact_result(artifact: ArtifactSpec, ctx: _Context) -> tuple[bool, str, str]:
    positions = ctx.facts.get("positions")
    if positions is not None and "{" in artifact.path:
        if not isinstance(positions, list) or not positions:
            return False, "position paths", "missing positions fact"
        results = [_artifact_result_at(artifact, ctx, item) for item in positions if isinstance(item, Mapping)]
        failed = [actual for passed, _, actual in results if not passed]
        return not failed and len(results) == len(positions), f"all {artifact.id} instances current", "; ".join(failed) or f"{len(results)} current"
    return _artifact_result_at(artifact, ctx)


def _artifact_result_at(artifact: ArtifactSpec, ctx: _Context, extra=None) -> tuple[bool, str, str]:
    try:
        path = _format_path(artifact, ctx, extra)
    except ValueError as exc:
        return False, f"resolved path for {artifact.id}", str(exc)
    if artifact.storage == "sqlite_data_access":
        exists, actual = _sqlite_artifact(artifact, path, ctx)
        passed = exists
    else:
        exists = path.exists()
        actual = (datetime.fromtimestamp(path.stat().st_mtime, ctx.timezone).isoformat()
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


def _evidence(gate: GateSpec, ctx: _Context, require_first_party=False) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if not isinstance(value, Mapping) or not isinstance(value.get("evidence"), list):
        return False, "structured evidence", "missing evidence list"
    entities = {str(x) for x in value.get("entities", [])}
    material_claims = {str(x) for x in value.get("material_claims", [])}
    covered_entities: set[str] = set()
    covered_claims: set[str] = set()
    errors = []
    for i, item in enumerate(value["evidence"]):
        required = {"claim_id", "entity", "material", "url", "publication_date", "source_tier", "verification_status"}
        if not isinstance(item, Mapping) or required - item.keys():
            errors.append(f"evidence[{i}] malformed")
            continue
        try:
            datetime.fromisoformat(str(item["publication_date"]))
        except ValueError:
            errors.append(f"evidence[{i}] undated")
            continue
        valid = str(item["url"]).startswith(("http://", "https://")) and item["verification_status"] == "verified"
        if require_first_party: valid = valid and item["source_tier"] in {"first_party", "authoritative"}
        if item["material"] is True and valid:
            covered_entities.add(str(item["entity"]))
            covered_claims.add(str(item["claim_id"]))
        elif item["material"] is True:
            errors.append(f"evidence[{i}] unverified")
    missing_entities = sorted(entities - covered_entities)
    missing_claims = sorted(material_claims - covered_claims)
    if missing_entities:
        errors.append("uncovered entities: " + ", ".join(missing_entities))
    if missing_claims:
        errors.append("uncovered claims: " + ", ".join(missing_claims))
    passed = not errors and bool(covered_claims)
    actual = "; ".join(errors) or f"covered claims: {', '.join(sorted(covered_claims))}"
    return passed, "all material claims and entities covered by dated verified evidence", actual


def _source_links(gate, ctx):
    return _evidence(gate, ctx)


def _source_verification(gate, ctx):
    return _evidence(gate, ctx, True)


def _decision_fields(gate, ctx):
    value = _fact(ctx, gate)
    decisions = value.get("decisions") if isinstance(value, Mapping) else None
    if not isinstance(decisions, list) or not decisions:
        return False, "decisions with price shares trigger invalidation", "missing decisions"
    fields = ("entity", "price", "shares", "trigger", "invalidation")
    missing = [
        f"decision[{i}]"
        for i, decision in enumerate(decisions)
        if not isinstance(decision, Mapping)
        or any(decision.get(key) in (None, "") for key in fields)
        or type(decision.get("shares")) is not int
        or decision["shares"] <= 0
    ]
    return not missing, "complete concrete decisions", ", ".join(missing) or f"{len(decisions)} complete"


def _test_verification(gate, ctx):
    value = _fact(ctx, gate)
    if not isinstance(value, Mapping):
        return False, "fresh successful commands and commit identity", "missing verification mapping"
    commands = value.get("commands")
    missing = [key for key in ("timestamp", "commit") if not value.get(key)]
    try:
        stamp = datetime.fromisoformat(str(value.get("timestamp", "")))
    except ValueError:
        stamp = None
    fresh = stamp is not None and abs(
        (ctx.now - stamp.astimezone(ctx.now.tzinfo)).total_seconds()
    ) <= 86400
    successful = isinstance(commands, list) and bool(commands) and all(
        isinstance(command, Mapping)
        and command.get("command")
        and command.get("exit_status") == 0
        and type(command.get("test_count")) is int
        for command in commands
    )
    passed = not missing and fresh and successful
    return passed, "fresh successful test commands with counts and commit", "verified" if passed else "invalid verification evidence"


def _git_commit_contains(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
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
    if value is not None and not isinstance(value, (bool, Mapping)):
        return False, "local Git publication proof", f"invalid boolean fact: {type(value).__name__}"
    paths: list[str] = []
    if isinstance(value, Mapping):
        raw_paths = value.get("paths", [])
        if not isinstance(raw_paths, list):
            return False, "publication paths list", "invalid paths fact"
        paths.extend(str(path) for path in raw_paths)
    if ctx.workflow in {"daily-report", "weekly-report", "deploy"}:
        if not isinstance(value, Mapping) or not isinstance(value.get("deployment"), Mapping):
            return False, "committed remote publication and verified deployment", "missing deployment evidence"
        deployment = value["deployment"]
        if not str(deployment.get("url", "")).startswith("https://") or deployment.get("verified") is not True:
            return False, "HTTPS publication URL verified true", "invalid deployment evidence"
    workflow = ctx.registry.workflows[ctx.workflow]
    for artifact_id in workflow.outputs:
        artifact = ctx.registry.artifacts.get(artifact_id)
        if artifact and artifact.storage == "filesystem":
            try:
                paths.append(str(_format_path(artifact, ctx).relative_to(ctx.root)))
            except ValueError:
                paths.append(artifact.path)
    positions = ctx.facts.get("positions", [])
    position_artifact = ctx.registry.artifacts.get("artifact.position")
    if position_artifact and isinstance(positions, list):
        for position in positions:
            if isinstance(position, Mapping):
                try: paths.append(str(_format_path(position_artifact, ctx, position).relative_to(ctx.root)))
                except (ValueError, KeyError): pass
    paths = sorted(set(paths))
    suffix = ["--", *paths] if paths else []
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all", *suffix],
            cwd=ctx.root, text=True, capture_output=True, check=False,
        )
        missing = []
        for path in paths:
            committed = subprocess.run(
                ["git", "cat-file", "-e", f"HEAD:{path}"], cwd=ctx.root,
                text=True, capture_output=True, check=False,
            )
            if committed.returncode:
                missing.append(path)
        ahead = subprocess.run(
            ["git", "rev-list", "--count", "@{upstream}..HEAD"],
            cwd=ctx.root, text=True, capture_output=True, check=False,
        )
        ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", "@{upstream}"], cwd=ctx.root, text=True, capture_output=True, check=False)
    except OSError as exc:
        return False, "clean committed publication paths and zero unpushed commits", f"git unavailable: {exc}"
    problems = []
    if value is False:
        problems.append("external fact is false")
    if status.returncode or status.stdout.strip():
        problems.append("dirty: " + (status.stdout.strip() or status.stderr.strip()))
    if missing:
        problems.append("not committed: " + ", ".join(missing))
    if ahead.returncode or ahead.stdout.strip() != "0":
        problems.append("unpushed: " + (ahead.stdout.strip() or ahead.stderr.strip()))
    if ancestor.returncode:
        problems.append("HEAD is not on expected remote branch")
    return not problems, "clean committed publication paths and zero unpushed commits", "; ".join(problems) or "pushed"


def _generated_docs_clean(gate: GateSpec, ctx: _Context) -> tuple[bool, str, str]:
    value = _fact(ctx, gate)
    if value is not None and not isinstance(value, Mapping):
        return False, "generated paths clean", f"invalid paths fact: {type(value).__name__}"
    paths = ["AGENTS.md", "references/skills-index.md", "references/generated/workflows.md"]
    if isinstance(value, Mapping):
        raw = value.get("paths", [])
        if not isinstance(raw, list):
            return False, "generated paths clean", "invalid paths fact"
        paths.extend(str(path) for path in raw)
    paths = sorted(set(paths))
    commands = (
        ["git", "diff", "--name-only", "--", *paths],
        ["git", "diff", "--cached", "--name-only", "--", *paths],
        ["git", "ls-files", "--others", "--exclude-standard", "--", *paths],
    )
    try:
        runs = [subprocess.run(command, cwd=ctx.root, text=True, capture_output=True, check=False) for command in commands]
    except OSError as exc:
        return False, "generated paths clean", f"git unavailable: {exc}"
    changed = sorted({line for run in runs for line in run.stdout.splitlines() if line})
    errors = [run.stderr.strip() for run in runs if run.returncode]
    passed = not changed and not errors
    return passed, "no unstaged, staged, or untracked generated documents", ", ".join(changed or errors) or "clean"


_EVALUATORS: dict[str, Callable[[GateSpec, _Context], tuple[bool, str, str]]] = {
    "path_exists": _path_exists, "json_field": _json_field,
    "artifact_freshness": _artifact_freshness, "markdown_sections": _markdown_sections,
    "source_links": _source_links,
    "source_verification": _source_verification, "decision_fields": _decision_fields,
    "test_verification": _test_verification,
    "git_commit_contains": _git_commit_contains,
    "git_pushed": _git_pushed,
    "generated_docs_clean": _generated_docs_clean,
}


def registered_evaluators() -> frozenset[str]:
    return frozenset(_EVALUATORS)


def check_workflow(workflow_id: str, phase: str, registry: SpecRegistry, repo_root: Path,
                   now: datetime | None = None, facts: Mapping[str, Any] | None = None) -> CheckReport:
    if phase == "all":
        first = check_workflow(workflow_id, "preflight", registry, repo_root, now, facts)
        second = check_workflow(workflow_id, "completion", registry, repo_root, now, facts)
        return CheckReport(workflow_id, "all", first.results + second.results)
    if phase not in {"preflight", "completion"}: raise ValueError(f"unknown phase: {phase}")
    if facts is not None and not isinstance(facts, Mapping):
        raise ValueError("facts must be a JSON object")
    workflow = registry.workflows[workflow_id]
    timezone_name = str(registry.project.get("timezone", "Asia/Shanghai"))
    try:
        project_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown project timezone: {timezone_name}") from exc
    current = now or datetime.now(project_timezone)
    if current.tzinfo is None:
        current = current.replace(tzinfo=project_timezone)
    ctx = _Context(workflow_id, phase, registry, Path(repo_root), current, facts or {}, project_timezone)
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
                severity = gate.severity
                try:
                    passed, expected, actual = evaluator(gate, ctx)
                except Exception as exc:  # evaluator failures are deterministic diagnostics
                    passed, expected, actual = False, "successful evaluator", f"evaluation error: {type(exc).__name__}: {exc}"
                    severity = "block"
            remediation = gate.remediation
        results.append(GateResult(entry, severity, passed, expected, actual, remediation))
    return CheckReport(workflow_id, phase, tuple(results))
