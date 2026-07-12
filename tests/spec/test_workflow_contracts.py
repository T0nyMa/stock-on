from pathlib import Path

import pytest

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
        assert workflow.on_failure


def test_representative_intents_have_unique_routes():
    registry = load_registry(ROOT / "spec")
    assert resolve_intent("日报", registry).workflow == "daily-report"
    assert resolve_intent("财报分析 阿里巴巴", registry).workflow == "financial-report"
    assert resolve_intent("深度分析 山东黄金", registry).workflow == "deep-research"
    assert resolve_intent("建仓分析 002050", registry).workflow == "position-decision"
    assert resolve_intent("筛选", registry).route_id == "screener"
    assert resolve_intent("热门股", registry).route_id == "screener"
    assert resolve_intent("板块扫描", registry).route_id == "sector-scan"
    assert resolve_intent("板块排名", registry).route_id == "sector-scan"
    assert resolve_intent("热点板块", registry).route_id == "sector-scan"


@pytest.mark.parametrize(
    ("text", "route_id", "workflow_id", "skill_id"),
    [
        ("深度分析 002050", "deep-research", "deep-research", "deep-stock-analysis"),
        ("深研 002050", "deep-research", "deep-research", "deep-stock-analysis"),
        ("财报分析 9988", "financial-report", "financial-report", "financial-report-analysis"),
        ("财报深度解析 9988", "financial-report", "financial-report", "financial-report-analysis"),
        ("财报排雷 9988", "financial-report", "financial-report", "financial-report-analysis"),
        ("财务质量 9988", "financial-report", "financial-report", "financial-report-analysis"),
        ("建仓分析 002050", "position-decision", "position-decision", "decision-agent"),
        ("新股票 002050", "position-decision", "position-decision", "decision-agent"),
        ("分析三花", "position-decision", "position-decision", "decision-agent"),
        ("今日002050", "position-decision", "position-decision", "decision-agent"),
        ("分析兆易创新", "position-decision", "position-decision", "decision-agent"),
        ("603986怎么样", "position-decision", "position-decision", "decision-agent"),
        ("扫描策略 002050", "strategy-analysis", "strategy-analysis", "strategy-executor"),
        ("策略分析 002050", "strategy-analysis", "strategy-analysis", "strategy-executor"),
        ("日报", "daily-report", "daily-report", "daily-report"),
        ("今日总结", "daily-report", "daily-report", "daily-report"),
        ("daily", "daily-report", "daily-report", "daily-report"),
        ("周报", "weekly-report", "weekly-report", "weekly-report"),
        ("本周总结", "weekly-report", "weekly-report", "weekly-report"),
        ("weekly", "weekly-report", "weekly-report", "weekly-report"),
        ("潜力股", "discovery", "discovery", "discovery"),
        ("发现股票", "discovery", "discovery", "discovery"),
        ("发现机会", "discovery", "discovery", "discovery"),
        ("discovery", "discovery", "discovery", "discovery"),
        ("筛选", "screener", "discovery", "screener"),
        ("热门股", "screener", "discovery", "screener"),
        ("板块扫描", "sector-scan", "discovery", "sector-scan"),
        ("板块排名", "sector-scan", "discovery", "sector-scan"),
        ("热点板块", "sector-scan", "discovery", "sector-scan"),
        ("发布", "deploy", "deploy", "deploy"),
        ("deploy", "deploy", "deploy", "deploy"),
    ],
)
def test_all_documented_intent_groups_resolve_to_the_expected_skill(
    text, route_id, workflow_id, skill_id
):
    registry = load_registry(ROOT / "spec")
    match = resolve_intent(text, registry)
    assert match.route_id == route_id
    assert match.workflow == workflow_id
    assert registry.routes[match.route_id].skill == skill_id


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


def test_daily_report_alone_satisfies_deploy_required_inputs():
    registry = load_registry(ROOT / "spec")
    deploy = registry.workflows["deploy"]
    assert deploy.inputs == ("artifact.daily_report",)
    assert set(deploy.optional_inputs) == {
        "artifact.weekly_report",
        "artifact.discovery_report",
    }
    assert set(deploy.inputs) <= set(registry.workflows["daily-report"].outputs)


def test_strategy_and_development_outputs_are_concrete_filesystem_records():
    registry = load_registry(ROOT / "spec")
    strategy = registry.artifacts["artifact.strategy_scan"]
    assert strategy.path == "data/{code}/strategy_scan.json"
    assert strategy.storage == "filesystem"
    assert strategy.kind == "strategy_scan"
    verification = registry.artifacts["artifact.verification_record"]
    assert verification.path == "data/spec/verification.json"
    assert verification.storage == "filesystem"
    assert verification.kind == "verification_record"
