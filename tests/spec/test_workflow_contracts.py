from pathlib import Path

from src.spec.loader import load_registry
from src.spec.router import resolve_intent


ROOT = Path(__file__).parents[2]
EXPECTED = {
    "development",
    "data-preparation",
    "quant-analysis",
    "strategy-analysis",
    "deep-research",
    "financial-report",
    "position-decision",
    "daily-report",
    "weekly-report",
    "discovery",
    "deploy",
}


def test_all_core_workflows_are_registered():
    registry = load_registry(ROOT / "spec")
    assert EXPECTED <= set(registry.workflows)
    for workflow_id in EXPECTED:
        workflow = registry.workflows[workflow_id]
        assert workflow.policies
        assert workflow.steps
        assert workflow.outputs


def test_representative_intents_have_unique_routes():
    registry = load_registry(ROOT / "spec")
    assert resolve_intent("日报", registry).workflow == "daily-report"
    assert resolve_intent("财报分析 阿里巴巴", registry).workflow == "financial-report"
    assert resolve_intent("深度分析 山东黄金", registry).workflow == "deep-research"
    assert resolve_intent("建仓分析 002050", registry).workflow == "position-decision"


def test_research_workflows_do_not_produce_trading_artifacts():
    registry = load_registry(ROOT / "spec")
    trading_artifacts = {"artifact.tracklist", "artifact.position"}
    assert not trading_artifacts.intersection(
        registry.workflows["deep-research"].outputs
    )
    assert not trading_artifacts.intersection(
        registry.workflows["financial-report"].outputs
    )


def test_position_decision_consumes_research_and_requires_specific_instructions():
    registry = load_registry(ROOT / "spec")
    workflow = registry.workflows["position-decision"]
    assert "artifact.research_summary" in workflow.inputs
    assert "artifact.financial_quality_summary" in workflow.inputs
    assert "DECISION.ACTION_SPECIFIC" in workflow.completion
    assert any(
        all(field in step for field in ("price", "shares", "trigger", "invalidation"))
        for step in workflow.steps
    )


def test_daily_report_completion_includes_deployment():
    registry = load_registry(ROOT / "spec")
    workflow = registry.workflows["daily-report"]
    assert "artifact.report_context" in workflow.inputs
    assert "SEARCH.MATERIAL_FACT_VERIFIED" in workflow.preflight
    assert "PUBLISH.PUSHED" in workflow.completion
    assert any("seven-section" in step for step in workflow.steps)
    assert any("deploy" in step for step in workflow.steps)
