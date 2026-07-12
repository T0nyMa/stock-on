from dataclasses import replace
from pathlib import Path
import re

import pytest

from src.spec.loader import load_registry


ROOT = Path(__file__).parents[2]
CONTRACT_SKILLS = {
    "daily-report",
    "weekly-report",
    "deploy",
    "deep-stock-analysis",
    "financial-report-analysis",
    "discovery",
    "screener",
    "sector-scan",
    "fetch-data",
    "tech-indicators",
    "decision-agent",
}
FIELDS = ("Workflow", "Policies", "Consumes", "Produces")
DIRECT_EASYANYSEARCH_MANDATES = (
    re.compile(r"必须使用\s*EasyAnySearch", re.IGNORECASE),
    re.compile(r"EasyAnySearch\s*负责(?:检索|搜索)", re.IGNORECASE),
    re.compile(r"(?:使用|用)\s*EasyAnySearch\s*(?:执行|检索|搜索)", re.IGNORECASE),
)


def parse_project_contract(text: str) -> dict[str, tuple[str, ...] | str]:
    marker = "## Project contract"
    assert text.count(marker) == 1, "expected exactly one Project contract section"
    block = text.split(marker, 1)[1].split("\n## ", 1)[0]
    values: dict[str, tuple[str, ...] | str] = {}
    for line in block.splitlines():
        if len(values) == len(FIELDS):
            break
        line = line.strip()
        if not line:
            continue
        assert line.startswith("- ") and ":" in line, f"invalid contract line: {line}"
        field, raw = line[2:].split(":", 1)
        assert field in FIELDS and field not in values, f"invalid contract field: {field}"
        items = tuple(item.strip().strip("`") for item in raw.split(",") if item.strip())
        assert items, f"empty contract field: {field}"
        if items == ("none",):
            items = ()
        values[field] = items[0] if field == "Workflow" else items
    assert tuple(values) == FIELDS, f"contract fields must be ordered as {FIELDS}"
    return values


def assert_contract_matches_registry(skill_id: str, contract: dict, registry) -> None:
    assert skill_id in registry.skills, f"unknown skill: {skill_id}"
    workflow_id = contract["Workflow"]
    assert workflow_id in registry.workflows, f"unknown workflow: {workflow_id}"
    workflow = registry.workflows[workflow_id]
    assert contract["Policies"] == workflow.policies
    assert contract["Consumes"] == workflow.inputs
    assert contract["Produces"] == workflow.outputs
    assert skill_id in workflow.skills, f"workflow missing skill reverse link: {skill_id}"
    assert workflow_id in registry.skills[skill_id].workflows, "skill missing workflow reverse link"


def test_core_skill_contracts_exactly_match_registry():
    registry = load_registry(ROOT / "spec")
    for skill_id in sorted(CONTRACT_SKILLS):
        path = ROOT / registry.skills[skill_id].path
        contract = parse_project_contract(path.read_text(encoding="utf-8"))
        assert_contract_matches_registry(skill_id, contract, registry)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Policies", ("DATA.QUALITY", "EXTRA.POLICY")),
        ("Consumes", ()),
        ("Consumes", ("artifact.daily_report",)),
        ("Produces", ("snapshot.quote",)),
    ],
)
def test_contract_validation_rejects_extra_missing_or_swapped_ids(field, value):
    registry = load_registry(ROOT / "spec")
    workflow = registry.workflows["daily-report"]
    contract = {
        "Workflow": workflow.id,
        "Policies": workflow.policies,
        "Consumes": workflow.inputs,
        "Produces": workflow.outputs,
    }
    contract[field] = value
    with pytest.raises(AssertionError):
        assert_contract_matches_registry("daily-report", contract, registry)


def test_contract_validation_rejects_wrong_reverse_link():
    registry = load_registry(ROOT / "spec")
    workflow = registry.workflows["daily-report"]
    registry.workflows[workflow.id] = replace(workflow, skills=("deploy",))
    contract = {
        "Workflow": workflow.id,
        "Policies": workflow.policies,
        "Consumes": workflow.inputs,
        "Produces": workflow.outputs,
    }
    with pytest.raises(AssertionError, match="reverse link"):
        assert_contract_matches_registry("daily-report", contract, registry)


def test_all_skill_markdown_has_no_direct_easyanysearch_mandate():
    conflicts = []
    for path in sorted((ROOT / ".agents/skills").glob("**/*.md")):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in DIRECT_EASYANYSEARCH_MANDATES):
                conflicts.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")
    assert not conflicts, "direct EasyAnySearch mandates conflict with SEARCH.PRIORITY:\n" + "\n".join(conflicts)
