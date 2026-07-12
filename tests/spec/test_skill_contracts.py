from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_orchestration_skills_reference_registered_workflows_and_policies():
    required = {
        "daily-report": ("workflow: daily-report", "SEARCH.PRIORITY", "PUBLISH.COMPLETE"),
        "financial-report-analysis": ("workflow: financial-report", "RESEARCH.EVIDENCE"),
        "deep-stock-analysis": ("workflow: deep-research", "DECISION.SEPARATION"),
        "deploy": ("workflow: deploy", "PUBLISH.COMPLETE"),
    }
    for skill, phrases in required.items():
        text = (ROOT / f".agents/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
        assert all(phrase in text for phrase in phrases), skill


def test_core_skills_declare_complete_registered_project_contracts():
    contracts = {
        "daily-report": ("daily-report", ["snapshot.quote", "artifact.daily_report"], ["DATA.QUALITY", "SEARCH.PRIORITY", "RESEARCH.EVIDENCE", "DECISION.SEPARATION", "PUBLISH.COMPLETE"]),
        "weekly-report": ("weekly-report", ["artifact.daily_report", "artifact.weekly_report"], ["DATA.QUALITY", "RESEARCH.EVIDENCE", "DECISION.SEPARATION", "PUBLISH.COMPLETE"]),
        "deploy": ("deploy", ["artifact.daily_report", "artifact.published_html"], ["PUBLISH.COMPLETE"]),
        "deep-stock-analysis": ("deep-research", ["snapshot.fundamentals", "artifact.research_summary"], ["DATA.QUALITY", "SEARCH.PRIORITY", "RESEARCH.EVIDENCE", "DECISION.SEPARATION"]),
        "financial-report-analysis": ("financial-report", ["snapshot.fundamentals", "artifact.financial_quality_summary"], ["DATA.QUALITY", "SEARCH.PRIORITY", "RESEARCH.EVIDENCE", "DECISION.SEPARATION"]),
        "discovery": ("discovery", ["snapshot.indicators", "artifact.discovery_report"], ["DATA.QUALITY", "RESEARCH.EVIDENCE"]),
        "screener": ("discovery", ["snapshot.indicators", "artifact.discovery_report"], ["DATA.QUALITY", "RESEARCH.EVIDENCE"]),
        "sector-scan": ("discovery", ["snapshot.indicators", "artifact.discovery_report"], ["DATA.QUALITY", "RESEARCH.EVIDENCE"]),
        "fetch-data": ("data-preparation", ["database.stock_analysis", "snapshot.news"], ["DATA.QUALITY", "SEARCH.PRIORITY"]),
        "tech-indicators": ("quant-analysis", ["database.stock_analysis", "artifact.report_context"], ["DATA.QUALITY"]),
        "decision-agent": ("position-decision", ["artifact.research_summary", "artifact.position"], ["DATA.QUALITY", "RESEARCH.EVIDENCE", "DECISION.SEPARATION"]),
    }
    for skill, (workflow, artifacts, policies) in contracts.items():
        text = (ROOT / f".agents/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
        contract = text.split("## Project contract", 1)[1].split("\n## ", 1)[0]
        assert f"workflow: {workflow}" in contract, skill
        assert all(artifact in contract for artifact in artifacts), skill
        assert all(policy in contract for policy in policies), skill
