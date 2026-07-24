from datetime import datetime
import json
from pathlib import Path

import pytest
import subprocess

from src.spec.cli import main
from src.spec.gates import check_workflow
from src.spec.loader import SpecLoadError, load_registry
from src.spec.validator import validate_registry
from src.spec.generator import render_workflows


ROOT = Path(__file__).parents[2]


def test_all_registered_evaluators_are_statically_known():
    registry = load_registry(ROOT / "spec")
    issues = validate_registry(registry, ROOT)
    assert not [issue for issue in issues if issue.code == "GATE.UNKNOWN_EVALUATOR"]


def test_generated_workflow_reference_includes_full_execution_contract():
    text = render_workflows(load_registry(ROOT / "spec"))
    for heading in ("Optional inputs", "Preflight", "Steps", "On failure"):
        assert heading in text


def test_check_phase_defaults_to_all(capsys):
    result = main(["--spec-root", str(ROOT / "spec"), "check", "--workflow", "development"])
    payload = json.loads(capsys.readouterr().out)
    assert result == 1
    assert payload["phase"] == "all"


def test_daily_publication_blocks_without_deployment_evidence(tmp_path):
    registry = load_registry(ROOT / "spec")
    result = check_workflow("daily-report", "completion", registry, tmp_path,
                            facts={"git_pushed": {"paths": []}})
    pushed = next(item for item in result.results if item.rule_id == "PUBLISH.PUSHED")
    assert not pushed.passed
    assert "missing deployment evidence" in pushed.actual


def test_daily_publication_blocks_dirty_applicable_position(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@y.test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "X"], cwd=tmp_path, check=True)
    paths = ["tracking/daily/positions/2026-07-12.md", "tracking/1-one/position.json", "index.html"]
    for relative in paths:
        path=tmp_path/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("base")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path/paths[1]).write_text("dirty")
    registry=load_registry(ROOT/"spec")
    facts={"positions":[{"code":"1","name":"one"}], "git_pushed":{"paths":[],"deployment":{"url":"https://example.test/report","verified":True}}}
    result=check_workflow("daily-report","completion",registry,tmp_path,now=datetime.fromisoformat("2026-07-12T11:00:00+08:00"),facts=facts)
    pushed=next(item for item in result.results if item.rule_id=="PUBLISH.PUSHED")
    assert not pushed.passed
    assert "position.json" in pushed.actual


@pytest.mark.parametrize("intent,workflow", [
    ("开发 修复bug", "development"),
    ("准备数据 002050", "data-preparation"),
    ("量化分析 002050", "quant-analysis"),
])
def test_every_core_capability_has_an_inspect_route(intent, workflow, capsys):
    assert main(["--spec-root", str(ROOT / "spec"), "inspect", "--intent", intent]) == 0
    assert json.loads(capsys.readouterr().out)["workflow"] == workflow


@pytest.mark.parametrize("check", ["source_verification", "decision_fields", "test_verification"])
def test_mandatory_evaluators_accept_structured_success_facts(check, tmp_path):
    registry = _single_gate_registry(tmp_path, check)
    facts = {
        "source_verification": {"evidence": [_evidence("c1", "002050")]},
        "decision_fields": {"decisions": [{"entity": "002050", "price": "20-21", "shares": 100, "trigger": "close above 20", "invalidation": "below 18"}]},
        "test_verification": {"commands": [{"command": "pytest", "exit_status": 0, "test_count": 3}], "timestamp": "2026-07-12T10:00:00+08:00", "commit": "abc123"},
    }
    context = {check: facts[check], "required_entities": ["002050"],
               "claim_manifest": [{"claim_id": "c1", "entity": "002050", "material": True}]}
    report = check_workflow("sample", "completion", registry, tmp_path,
                            now=datetime.fromisoformat("2026-07-12T11:00:00+08:00"), facts=context)
    assert report.ok, report.to_dict()


def test_evidence_requires_dated_verified_coverage_for_each_entity(tmp_path):
    registry = _single_gate_registry(tmp_path, "source_links")
    partial = {"evidence": [_evidence("c1", "A")]}
    facts = {"required_entities": ["A", "B"], "claim_manifest": [
        {"claim_id": "c1", "entity": "A", "material": True},
        {"claim_id": "c2", "entity": "B", "material": True}], "source_links": partial}
    result = check_workflow("sample", "completion", registry, tmp_path, facts=facts)
    assert not result.ok
    assert "B" in result.results[0].actual
    assert "c2" in result.results[0].actual


def test_evidence_rejects_missing_independent_manifest(tmp_path):
    registry = _single_gate_registry(tmp_path, "source_verification")
    facts = {"required_entities": ["A"], "source_verification": {"evidence": [_evidence("c1", "A")]}}
    result = check_workflow("sample", "completion", registry, tmp_path, facts=facts)
    assert not result.ok
    assert "claim_manifest" in result.results[0].actual


def test_evidence_rejects_cross_wired_claim_entity_pairs(tmp_path):
    registry = _single_gate_registry(tmp_path, "source_verification")
    facts = {"required_entities": ["A", "B"], "claim_manifest": [
        {"claim_id": "c1", "entity": "A", "material": True},
        {"claim_id": "c2", "entity": "B", "material": True}],
        "source_verification": {"evidence": [_evidence("c1", "B"), _evidence("c2", "A")]}}
    result = check_workflow("sample", "completion", registry, tmp_path, facts=facts)
    assert not result.ok
    assert "unmanifested evidence pair" in result.results[0].actual


@pytest.mark.parametrize("manifest,diagnostic", [
    ([{"claim_id": "c1", "entity": "A", "material": True},
      {"claim_id": "c1", "entity": "A", "material": True}], "duplicate claim_id"),
    ([{"claim_id": "c1", "entity": "A", "material": True},
      {"claim_id": "c1", "entity": "B", "material": True}], "duplicate claim_id"),
    ([{"claim_id": "c1", "entity": "C", "material": True}], "outside required_entities"),
    ([{"claim_id": "c1", "entity": "", "material": True}], "malformed"),
])
def test_evidence_rejects_duplicate_conflicting_or_invalid_manifest(tmp_path, manifest, diagnostic):
    registry = _single_gate_registry(tmp_path, "source_links")
    facts = {"required_entities": ["A", "B"], "claim_manifest": manifest,
             "source_links": {"evidence": [_evidence("c1", "A")]}}
    result = check_workflow("sample", "completion", registry, tmp_path, facts=facts)
    assert not result.ok
    assert diagnostic in result.results[0].actual


def test_evidence_rejects_unmanifested_evidence_pair(tmp_path):
    registry = _single_gate_registry(tmp_path, "source_links")
    facts = {"required_entities": ["A"], "claim_manifest": [
        {"claim_id": "c1", "entity": "A", "material": True}],
        "source_links": {"evidence": [_evidence("c1", "A"), _evidence("extra", "A")]}}
    result = check_workflow("sample", "completion", registry, tmp_path, facts=facts)
    assert not result.ok
    assert "unmanifested evidence pair" in result.results[0].actual


def test_evidence_accepts_exact_multi_entity_pairs(tmp_path):
    registry = _single_gate_registry(tmp_path, "source_verification")
    facts = {"required_entities": ["A", "B"], "claim_manifest": [
        {"claim_id": "c1", "entity": "A", "material": True},
        {"claim_id": "c2", "entity": "B", "material": True}],
        "source_verification": {"evidence": [_evidence("c1", "A"), _evidence("c2", "B")]}}
    assert check_workflow("sample", "completion", registry, tmp_path, facts=facts).ok


@pytest.mark.parametrize("field,value", [
    ("entity", True), ("entity", ""), ("trigger", []), ("invalidation", {}),
    ("shares", True), ("shares", 0), ("shares", -1),
    ("price", True), ("price", 0), ("price", -1), ("price", float("nan")),
    ("price", float("inf")), ("price", []), ("price", {}),
    ("price", "2-1"), ("price", "0-2"), ("price", "one-two"),
])
def test_decision_fields_rejects_exact_invalid_boundaries(tmp_path, field, value):
    registry = _single_gate_registry(tmp_path, "decision_fields")
    decision = {"entity": "A", "price": "1-2", "shares": 1,
                "trigger": "go", "invalidation": "stop"}
    decision[field] = value
    facts = {"required_entities": ["A"], "decision_fields": {"decisions": [decision]}}
    assert not check_workflow("sample", "completion", registry, tmp_path, facts=facts).ok


def test_decision_fields_requires_independent_entity_coverage(tmp_path):
    registry = _single_gate_registry(tmp_path, "decision_fields")
    decision = {"entity": "A", "price": 1.5, "shares": 1,
                "trigger": "go", "invalidation": "stop"}
    facts = {"required_entities": ["A", "B"], "decision_fields": {"decisions": [decision]}}
    result = check_workflow("sample", "completion", registry, tmp_path, facts=facts)
    assert not result.ok
    assert "B" in result.results[0].actual


def test_unresolved_artifact_template_is_specific_blocking_diagnostic(tmp_path):
    registry = _artifact_registry(tmp_path)
    result = check_workflow("sample", "preflight", registry, tmp_path, facts={"params": {"code": "1"}})
    assert not result.ok
    assert "unresolved template parameters: name" in result.results[0].actual


def test_multi_position_artifact_checks_each_position(tmp_path):
    registry = _artifact_registry(tmp_path)
    for code, name in (("1", "one"), ("2", "two")):
        path = tmp_path / f"tracking/{code}-{name}/position.json"
        path.parent.mkdir(parents=True)
        path.write_text("{}")
    facts = {"positions": [{"code": "1", "name": "one"}, {"code": "2", "name": "two"}]}
    assert check_workflow("sample", "preflight", registry, tmp_path, facts=facts).ok


def test_position_manifest_does_not_expand_date_only_artifacts(tmp_path):
    root = _base_spec(tmp_path)
    (root / "artifacts.yaml").write_text(
        "- id: report\n"
        "  path: reports/{date}.md\n"
        "  producer: sample\n"
        "  consumers: []\n"
        "  freshness: trading_day\n"
        "  missing: block\n"
    )
    (root / "policies/p.yaml").write_text("id: p\ndescription: p\ngates: []\n")
    (root / "workflows/sample.yaml").write_text(
        "id: sample\ninputs: [report]\noptional_inputs: []\noutputs: []\n"
        "policies: [p]\nskills: []\nsteps: [s]\npreflight: [report]\n"
        "completion: []\non_failure: [stop]\n"
    )
    report = tmp_path / "reports/2026-07-24.md"
    report.parent.mkdir()
    report.write_text("ok")
    facts = {
        "positions": [
            {"code": "1", "name": "one"},
            {"code": "2", "name": "two"},
        ]
    }
    result = check_workflow(
        "sample",
        "preflight",
        load_registry(root),
        tmp_path,
        now=datetime.fromisoformat("2026-07-24T21:00:00+08:00"),
        facts=facts,
    )
    assert result.ok
    assert result.results[0].actual != "2 current"


@pytest.mark.parametrize("mutation,error", [
    ("priority: nope", "expected integer for priority"),
    ("intents: [ok, 1]", "expected string element for intents"),
    ("mystery: value", "unknown key: mystery"),
])
def test_loader_rejects_bad_scalar_elements_and_unknown_keys(tmp_path, mutation, error):
    spec = _base_spec(tmp_path)
    route = "id: r\nintents: [ok]\nworkflow: sample\npriority: 1\n" + mutation + "\n"
    (spec / "routes.yaml").write_text(route)
    with pytest.raises(SpecLoadError, match=error):
        load_registry(spec)


@pytest.mark.parametrize("yaml,error", [
    ('timezone: []', "timezone"),
    ('timezone: Not/AZone', "timezone"),
    ('principles: wrong', "principles"),
    ('principles: [ok, 1]', "principles"),
    ('runtime: wrong', "runtime"),
    ('runtime: {unknown: x}', "runtime unknown key"),
    ('runtime: {python: 3}', "runtime.python"),
    ('ownership: wrong', "ownership"),
    ('ownership: {src/: ""}', "ownership"),
    ('owners: {spec/: 1}', "owners"),
])
def test_project_optional_fields_have_strict_nested_schema(tmp_path, yaml, error):
    spec = _base_spec(tmp_path)
    (spec / "project.yaml").write_text(f'schema_version: "1.0"\nproject: x\n{yaml}\n')
    with pytest.raises(SpecLoadError, match=error):
        load_registry(spec)


def _evidence(claim, entity):
    return {"claim_id": claim, "entity": entity, "material": True,
            "url": "https://example.test/source", "publication_date": "2026-07-12",
            "source_tier": "first_party", "verification_status": "verified"}


def _base_spec(tmp_path):
    root = tmp_path / "spec"; (root / "policies").mkdir(parents=True); (root / "workflows").mkdir()
    (root / "project.yaml").write_text('schema_version: "1.0"\nproject: x\n')
    (root / "routes.yaml").write_text("[]\n"); (root / "artifacts.yaml").write_text("[]\n"); (root / "skills.yaml").write_text("[]\n")
    return root


def _single_gate_registry(tmp_path, check):
    root = _base_spec(tmp_path)
    (root / "policies/p.yaml").write_text(f"id: p\ndescription: p\ngates:\n  - id: G\n    severity: block\n    check: {check}\n    message: m\n    remediation: r\n")
    (root / "workflows/sample.yaml").write_text("id: sample\ninputs: []\noptional_inputs: []\noutputs: []\npolicies: [p]\nskills: []\nsteps: [s]\npreflight: []\ncompletion: [G]\non_failure: [stop]\n")
    return load_registry(root)


def _artifact_registry(tmp_path):
    root = _base_spec(tmp_path)
    (root / "artifacts.yaml").write_text("- id: position\n  path: tracking/{code}-{name}/position.json\n  producer: sample\n  consumers: [sample]\n  freshness: current\n  missing: block\n")
    (root / "policies/p.yaml").write_text("id: p\ndescription: p\ngates: []\n")
    (root / "workflows/sample.yaml").write_text("id: sample\ninputs: [position]\noptional_inputs: []\noutputs: [position]\npolicies: [p]\nskills: []\nsteps: [s]\npreflight: [position]\ncompletion: []\non_failure: [stop]\n")
    return load_registry(root)
