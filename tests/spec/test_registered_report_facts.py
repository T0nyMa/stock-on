from datetime import datetime
from pathlib import Path

import pytest

from src.spec.facts import load_workflow_facts
from src.spec.gates import check_workflow
from src.spec.loader import load_registry


ROOT = Path(__file__).parents[2]
NOW = datetime.fromisoformat("2026-07-24T21:00:00+08:00")


@pytest.mark.parametrize("workflow", ["daily-report", "weekly-report"])
def test_registered_report_facts_cover_evidence_decisions_and_positions(workflow):
    facts = load_workflow_facts(ROOT, workflow)
    assert len(facts["positions"]) == 4
    result = check_workflow(
        workflow, "completion", load_registry(ROOT / "spec"), ROOT, now=NOW, facts=facts
    )
    by_id = {item.rule_id: item for item in result.results}
    assert by_id["RESEARCH.SOURCES_BOUND"].passed, by_id[
        "RESEARCH.SOURCES_BOUND"
    ].actual
    assert by_id["DECISION.ACTION_SPECIFIC"].passed, by_id[
        "DECISION.ACTION_SPECIFIC"
    ].actual
    assert by_id["artifact.position"].passed, by_id["artifact.position"].actual


def test_registered_weekly_artifact_uses_report_date_path():
    facts = load_workflow_facts(ROOT, "weekly-report")
    result = check_workflow(
        "weekly-report",
        "completion",
        load_registry(ROOT / "spec"),
        ROOT,
        now=NOW,
        facts=facts,
    )
    weekly = next(item for item in result.results if item.rule_id == "DATA.REGISTERED_CURRENT")
    assert weekly.passed, weekly.actual
