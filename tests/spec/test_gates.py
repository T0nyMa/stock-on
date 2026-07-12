import json
import sqlite3
from datetime import datetime, timezone
import os
from pathlib import Path

from src.spec.gates import CheckReport, GateResult, check_workflow
from src.spec.loader import load_registry
from src.spec.models import GateSpec, SpecRegistry, WorkflowSpec


FIXTURE = Path(__file__).parent / "fixtures/minimal"


def test_block_failure_fails_report_but_warning_does_not():
    blocked = CheckReport("daily-report", "preflight", (GateResult("A", "block", False, "expected", "actual", "fix"),))
    warned = CheckReport("daily-report", "preflight", (GateResult("B", "warn", False, "expected", "actual", "fix"),))
    assert blocked.ok is False
    assert warned.ok is True
    informed = CheckReport("daily-report", "preflight", (GateResult("C", "info", False, "expected", "actual", "fix"),))
    assert informed.ok is True


def test_gate_result_serializes_required_diagnostics():
    result = GateResult("DATA.CURRENT", "block", False, "today", "yesterday", "run fetch")
    assert result.to_dict() == {"rule_id":"DATA.CURRENT","severity":"block","passed":False,"expected":"today","actual":"yesterday","remediation":"run fetch"}


def test_missing_path_fact_is_blocking():
    report = check_workflow("sample", "preflight", load_registry(FIXTURE), Path("."))
    result = report.results[0]
    assert (report.ok, result.severity, result.actual) == (False, "block", "missing path fact")


def test_artifact_freshness_requires_specific_sqlite_snapshot_kind(tmp_path):
    spec = tmp_path / "spec"
    (spec / "policies").mkdir(parents=True)
    (spec / "workflows").mkdir()
    for name in ("routes.yaml", "skills.yaml"):
        (spec / name).write_text("[]\n")
    (spec / "project.yaml").write_text('schema_version: "1.0"\nproject: test\n')
    (spec / "artifacts.yaml").write_text("""- id: snapshot.quote
  path: data/test.db
  storage: sqlite_data_access
  kind: quote
  producer: sample
  consumers: [sample]
  freshness: trading_day
  missing: block
""")
    (spec / "policies/data.yaml").write_text("""id: p
description: data
gates:
  - id: DATA.CURRENT
    severity: block
    check: artifact_freshness
    message: current
    remediation: fetch
""")
    (spec / "workflows/sample.yaml").write_text("""id: sample
inputs: [snapshot.quote]
optional_inputs: []
outputs: []
policies: [p]
skills: []
steps: []
preflight: [snapshot.quote]
completion: [DATA.CURRENT]
on_failure: []
""")
    db = tmp_path / "data/test.db"
    db.parent.mkdir()
    with sqlite3.connect(db) as conn:
        conn.execute("create table stock_snapshots (code text, kind text, updated_at text)")
        conn.execute("insert into stock_snapshots values ('A', 'news', '2026-07-12T09:00:00')")
    registry = load_registry(spec)
    missing = check_workflow("sample", "preflight", registry, tmp_path, now=datetime(2026, 7, 12, 12))
    assert missing.ok is False
    with sqlite3.connect(db) as conn:
        conn.execute("insert into stock_snapshots values ('A', 'quote', '2026-07-12T09:00:00')")
    current = check_workflow("sample", "preflight", registry, tmp_path, now=datetime(2026, 7, 12, 12))
    assert current.ok is True

    required = check_workflow(
        "sample", "preflight", registry, tmp_path,
        now=datetime(2026, 7, 12, 12), facts={"codes": ["A", "B"]},
    )
    assert required.ok is False
    assert "B" in required.results[0].actual
    parameterized = check_workflow(
        "sample", "preflight", registry, tmp_path,
        now=datetime(2026, 7, 12, 12), facts={"params": {"code": "B"}},
    )
    assert parameterized.ok is False
    assert "B=missing" in parameterized.results[0].actual
    with sqlite3.connect(db) as conn:
        conn.execute("insert into stock_snapshots values ('B', 'quote', '2026-07-11T15:00:00')")
    stale = check_workflow(
        "sample", "preflight", registry, tmp_path,
        now=datetime(2026, 7, 12, 12), facts={"codes": ["A", "B"]},
    )
    assert stale.ok is False
    assert "B=2026-07-11T15:00:00" in stale.results[0].actual


def _gate_registry(check, *, severity="block", outputs=(), project=None):
    gate = GateSpec("GATE", severity, check, "message", "fix")
    workflow = WorkflowSpec("sample", (), (), outputs, (), (), (), ("GATE",), ("GATE",), ())
    return SpecRegistry(Path("."), project or {}, {}, {}, {}, {}, {"sample": workflow}, {"GATE": gate})


def _git(repo, *args):
    import subprocess
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)


def test_generated_docs_clean_detects_staged_and_untracked_files(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "AGENTS.md").write_text("base")
    _git(tmp_path, "add", "AGENTS.md")
    _git(tmp_path, "commit", "-m", "base")
    registry = _gate_registry("generated_docs_clean")
    (tmp_path / "AGENTS.md").write_text("staged")
    _git(tmp_path, "add", "AGENTS.md")
    assert check_workflow("sample", "preflight", registry, tmp_path).ok is False
    _git(tmp_path, "reset", "--hard", "HEAD")
    (tmp_path / "references/generated").mkdir(parents=True)
    (tmp_path / "references/generated/workflows.md").write_text("untracked")
    assert check_workflow("sample", "preflight", registry, tmp_path).ok is False


def test_git_pushed_rejects_truthy_non_boolean_fact(tmp_path):
    registry = _gate_registry("git_pushed")
    result = check_workflow(
        "sample", "preflight", registry, tmp_path, facts={"git_pushed": "true"}
    ).results[0]
    assert result.passed is False
    assert "boolean" in result.actual


def test_git_pushed_requires_clean_committed_paths_and_no_ahead_commits(tmp_path):
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(tmp_path, "init", "--bare", str(remote))
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "report.md").write_text("one")
    _git(repo, "add", "report.md")
    _git(repo, "commit", "-m", "one")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-u", "origin", "HEAD")
    registry = _gate_registry("git_pushed")
    facts = {"git_pushed": {"paths": ["report.md"]}}
    assert check_workflow("sample", "preflight", registry, repo, facts=facts).ok is True
    (repo / "report.md").write_text("staged")
    _git(repo, "add", "report.md")
    assert check_workflow("sample", "preflight", registry, repo, facts=facts).ok is False
    _git(repo, "reset", "--hard", "HEAD")
    (repo / "other.md").write_text("untracked")
    untracked = {"git_pushed": {"paths": ["other.md"]}}
    assert check_workflow("sample", "preflight", registry, repo, facts=untracked).ok is False
    (repo / "other.md").unlink()
    (repo / "report.md").write_text("two")
    _git(repo, "add", "report.md")
    _git(repo, "commit", "-m", "two")
    result = check_workflow("sample", "preflight", registry, repo, facts=facts)
    assert result.ok is False
    assert "unpushed: 1" in result.results[0].actual


def test_filesystem_freshness_uses_asia_shanghai_for_mtime_boundary(tmp_path):
    spec = tmp_path / "spec"
    (spec / "policies").mkdir(parents=True)
    (spec / "workflows").mkdir()
    (spec / "routes.yaml").write_text("[]\n")
    (spec / "skills.yaml").write_text("[]\n")
    (spec / "project.yaml").write_text('schema_version: "1.0"\nproject: test\ntimezone: Asia/Shanghai\n')
    (spec / "artifacts.yaml").write_text("""- id: output
  path: output.md
  producer: sample
  consumers: []
  freshness: trading_day
  missing: block
""")
    (spec / "policies/p.yaml").write_text("""id: p
description: p
gates: []
""")
    (spec / "workflows/sample.yaml").write_text("""id: sample
inputs: [output]
optional_inputs: []
outputs: []
policies: [p]
skills: []
steps: []
preflight: [output]
completion: []
on_failure: []
""")
    output = tmp_path / "output.md"
    output.write_text("x")
    boundary = datetime(2026, 7, 11, 16, 30, tzinfo=timezone.utc).timestamp()
    os.utime(output, (boundary, boundary))
    report = check_workflow(
        "sample", "preflight", load_registry(spec), tmp_path,
        now=datetime(2026, 7, 12, 1, tzinfo=timezone.utc),
    )
    assert report.ok is True


def test_path_json_markdown_and_source_evaluators(tmp_path):
    (tmp_path / "exists.txt").write_text("x")
    path_report = check_workflow(
        "sample", "preflight", _gate_registry("path_exists"), tmp_path,
        facts={"path_exists": "exists.txt"},
    )
    assert path_report.ok is True

    (tmp_path / "value.json").write_text('{"nested":{"ready":true}}')
    json_report = check_workflow(
        "sample", "preflight", _gate_registry("json_field"), tmp_path,
        facts={"json_field": {"path": "value.json", "field": "nested.ready", "expected": True}},
    )
    assert json_report.ok is True

    (tmp_path / "report.md").write_text("# One\n\n# Two\n")
    markdown_report = check_workflow(
        "sample", "preflight", _gate_registry("markdown_sections"), tmp_path,
        facts={"markdown_sections": {"path": "report.md", "sections": ["# One", "# Missing"]}},
    )
    assert markdown_report.ok is False
    assert "# Missing" in markdown_report.results[0].actual

    source_report = check_workflow(
        "sample", "preflight", _gate_registry("source_links"), tmp_path,
        facts={"required_entities": ["sample"],
               "claim_manifest": [{"claim_id": "claim-1", "entity": "sample", "material": True}],
               "source_links": {"evidence": [{
            "claim_id": "claim-1", "entity": "sample", "material": True,
            "url": "https://example.test/source", "publication_date": "2026-07-12",
            "source_tier": "authoritative", "verification_status": "verified",
        }]}},
    )
    assert source_report.ok is True


def test_git_commit_contains_reads_commit_instead_of_boolean_override(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "report.md").write_text("published")
    _git(tmp_path, "add", "report.md")
    _git(tmp_path, "commit", "-m", "report")
    registry = _gate_registry("git_commit_contains")
    passed = check_workflow(
        "sample", "preflight", registry, tmp_path,
        facts={"git_commit_contains": {"path": "report.md", "contains": "published"}},
    )
    bypass = check_workflow(
        "sample", "preflight", registry, tmp_path, facts={"git_commit_contains": True},
    )
    assert passed.ok is True
    assert bypass.ok is False


def test_phase_selects_only_requested_gate_entries(tmp_path):
    gate = GateSpec("PRE", "warn", "path_exists", "message", "fix")
    completion = GateSpec("DONE", "block", "path_exists", "message", "fix")
    workflow = WorkflowSpec("sample", (), (), (), (), (), (), ("PRE",), ("DONE",), ())
    registry = SpecRegistry(Path("."), {}, {}, {}, {}, {}, {"sample": workflow}, {"PRE": gate, "DONE": completion})
    report = check_workflow(
        "sample", "completion", registry, tmp_path, facts={"path_exists": "missing"}
    )
    assert [result.rule_id for result in report.results] == ["DONE"]
    assert report.ok is False


def test_evaluator_exception_becomes_blocking_diagnostic(tmp_path, monkeypatch):
    import src.spec.gates as gates
    registry = _gate_registry("path_exists")
    monkeypatch.setitem(gates._EVALUATORS, "path_exists", lambda gate, ctx: 1 / 0)
    result = check_workflow("sample", "preflight", registry, tmp_path).results[0]
    assert result.passed is False
    assert "evaluation error: ZeroDivisionError" in result.actual


def test_warn_and_info_evaluator_exceptions_force_block_severity(tmp_path, monkeypatch):
    import src.spec.gates as gates
    monkeypatch.setitem(gates._EVALUATORS, "path_exists", lambda gate, ctx: 1 / 0)
    for severity in ("warn", "info"):
        report = check_workflow(
            "sample", "preflight", _gate_registry("path_exists", severity=severity), tmp_path
        )
        assert report.results[0].severity == "block"
        assert report.ok is False


def test_generated_docs_facts_paths_cannot_narrow_registered_defaults(tmp_path):
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "AGENTS.md").write_text("base")
    (tmp_path / "extra.md").write_text("base")
    _git(tmp_path, "add", "AGENTS.md", "extra.md")
    _git(tmp_path, "commit", "-m", "base")
    (tmp_path / "AGENTS.md").write_text("dirty default")
    registry = _gate_registry("generated_docs_clean")
    for supplied in ([], ["extra.md"]):
        report = check_workflow(
            "sample", "preflight", registry, tmp_path,
            facts={"generated_docs_clean": {"paths": supplied}},
        )
        assert report.ok is False
        assert "AGENTS.md" in report.results[0].actual
