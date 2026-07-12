from pathlib import Path

from src.spec.loader import load_registry
from src.spec.validator import validate_registry


ROOT = Path(__file__).parents[2]


def test_required_policies_and_search_order_are_registered():
    registry = load_registry(ROOT / "spec")
    assert {
        "DEV.CHANGE",
        "DATA.QUALITY",
        "SEARCH.PRIORITY",
        "RESEARCH.EVIDENCE",
        "DECISION.SEPARATION",
        "PUBLISH.COMPLETE",
    } <= set(registry.policies)
    search = registry.policies["SEARCH.PRIORITY"]
    assert "AnySearch" in search.description
    assert "EasyAnySearch" in search.description


def test_all_project_skill_directories_are_registered():
    registry = load_registry(ROOT / "spec")
    actual = {p.parent.name for p in (ROOT / ".agents/skills").glob("*/SKILL.md")}
    assert actual == set(registry.skills)


def test_registry_has_no_blocking_static_issues():
    registry = load_registry(ROOT / "spec")
    assert not [
        issue
        for issue in validate_registry(registry, ROOT)
        if issue.severity == "block"
    ]


def test_artifact_storage_matches_repository_contracts():
    registry = load_registry(ROOT / "spec")

    position = registry.artifacts["artifact.position"]
    assert position.path == "tracking/{code}-{name}/position.json"
    assert position.storage == "filesystem"

    sqlite_kinds = {
        "snapshot.bars": "bars",
        "snapshot.quote": "quote",
        "snapshot.fundamentals": "fundamentals",
        "snapshot.news": "news",
        "snapshot.indicators": "indicators",
        "artifact.research_summary": "research_summary",
        "artifact.financial_collection_status": "financial_collection_status",
        "artifact.financial_quality_summary": "financial_quality_summary",
    }
    for artifact_id, kind in sqlite_kinds.items():
        artifact = registry.artifacts[artifact_id]
        assert artifact.path == "data/stock_analysis.db"
        assert artifact.storage == "sqlite_data_access"
        assert artifact.kind == kind

    assert registry.artifacts["artifact.published_html"].path == "index.html"
