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
