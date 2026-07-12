from dataclasses import replace
from pathlib import Path

from src.spec.loader import load_registry
from src.spec.models import ArtifactSpec, RouteSpec, SkillSpec, WorkflowSpec
from src.spec.validator import has_blocking_issues, validate_registry


FIXTURE = Path(__file__).parent / "fixtures/minimal"


def test_unknown_workflow_and_skill_are_reported():
    registry = load_registry(FIXTURE)
    bad = replace(
        registry,
        routes={
            "route.bad": RouteSpec(
                "route.bad", ("bad",), "missing", "missing-skill", 1
            )
        },
    )
    codes = {issue.code for issue in validate_registry(bad, FIXTURE)}
    assert {"ROUTE.UNKNOWN_WORKFLOW", "ROUTE.UNKNOWN_SKILL"} <= codes


def test_duplicate_intent_at_same_priority_is_error():
    registry = load_registry(FIXTURE)
    routes = dict(registry.routes)
    routes["route.duplicate"] = RouteSpec(
        "route.duplicate", ("sample {stock}",), "sample", "sample-skill", 10
    )
    bad = replace(registry, routes=routes)
    assert any(
        issue.code == "ROUTE.AMBIGUOUS"
        for issue in validate_registry(bad, FIXTURE)
    )


def test_workflow_references_and_artifact_contracts_are_validated():
    registry = load_registry(FIXTURE)
    workflow = replace(
        registry.workflows["sample"],
        inputs=("artifact.missing",),
        outputs=("artifact.output",),
        policies=("policy.missing",),
        skills=("skill.missing",),
        preflight=("GATE.MISSING",),
    )
    artifact = replace(registry.artifacts["artifact.output"], producer="other")
    bad = replace(
        registry,
        workflows={"sample": workflow},
        artifacts={"artifact.output": artifact},
    )
    codes = {issue.code for issue in validate_registry(bad, FIXTURE)}
    assert {
        "WORKFLOW.UNKNOWN_ARTIFACT",
        "WORKFLOW.UNKNOWN_POLICY",
        "WORKFLOW.UNKNOWN_SKILL",
        "WORKFLOW.UNKNOWN_GATE",
        "ARTIFACT.PRODUCER_MISMATCH",
    } <= codes


def test_missing_skill_path_and_reverse_links_are_reported():
    registry = load_registry(FIXTURE)
    skill = SkillSpec("skill.sample", "does/not/exist.md", "test", (), ())
    artifact = replace(registry.artifacts["artifact.output"], consumers=("missing",))
    bad = replace(
        registry,
        skills={skill.id: skill},
        artifacts={artifact.id: artifact},
    )
    codes = {issue.code for issue in validate_registry(bad, FIXTURE)}
    assert {
        "SKILL.PATH_MISSING",
        "WORKFLOW.SKILL_MISMATCH",
        "ARTIFACT.UNKNOWN_CONSUMER",
    } <= codes


def test_artifact_dependency_cycle_is_reported():
    registry = load_registry(FIXTURE)
    one = ArtifactSpec("artifact.one", "one", "one", ("two",), "daily", "block")
    two = ArtifactSpec("artifact.two", "two", "two", ("one",), "daily", "block")
    workflow_one = WorkflowSpec("one", ("artifact.two",), ("artifact.one",), (), (), (), (), ())
    workflow_two = WorkflowSpec("two", ("artifact.one",), ("artifact.two",), (), (), (), (), ())
    bad = replace(
        registry,
        artifacts={one.id: one, two.id: two},
        workflows={"one": workflow_one, "two": workflow_two},
        routes={}, skills={}, policies={}, gates={},
    )
    assert any(issue.code == "WORKFLOW.DEPENDENCY_CYCLE" for issue in validate_registry(bad, FIXTURE))


def test_schema_markers_and_legacy_references_are_validated(tmp_path):
    registry = replace(load_registry(FIXTURE), project={"schema_version": "2.0", "project": "x"})
    (tmp_path / "AGENTS.md").write_text(
        "<!-- BEGIN GENERATED: routes -->\n.claude/skills/old/skill.md\n",
        encoding="utf-8",
    )
    issues = validate_registry(registry, tmp_path)
    codes = {issue.code for issue in issues}
    assert {"SCHEMA.UNSUPPORTED_VERSION", "GENERATED.MARKER_UNPAIRED", "DOC.FORBIDDEN_CLAUDE_SKILL"} <= codes
    assert has_blocking_issues(issues)
