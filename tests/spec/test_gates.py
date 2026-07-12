import json
import sqlite3
from datetime import datetime
from pathlib import Path

from src.spec.gates import CheckReport, GateResult, check_workflow
from src.spec.loader import load_registry


FIXTURE = Path(__file__).parent / "fixtures/minimal"


def test_block_failure_fails_report_but_warning_does_not():
    blocked = CheckReport("daily-report", "preflight", (GateResult("A", "block", False, "expected", "actual", "fix"),))
    warned = CheckReport("daily-report", "preflight", (GateResult("B", "warn", False, "expected", "actual", "fix"),))
    assert blocked.ok is False
    assert warned.ok is True


def test_gate_result_serializes_required_diagnostics():
    result = GateResult("DATA.CURRENT", "block", False, "today", "yesterday", "run fetch")
    assert result.to_dict() == {"rule_id":"DATA.CURRENT","severity":"block","passed":False,"expected":"today","actual":"yesterday","remediation":"run fetch"}


def test_unknown_evaluator_is_a_blocking_configuration_error():
    report = check_workflow("sample", "preflight", load_registry(FIXTURE), Path("."))
    result = report.results[0]
    assert (report.ok, result.severity, result.actual) == (False, "block", "unknown evaluator: output exists")


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
