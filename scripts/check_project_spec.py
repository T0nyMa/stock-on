#!/usr/bin/env python3
"""Run the repository's complete project-specification integrity gate."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.spec.generator import GeneratedSectionError, generate_documents
from src.spec.loader import SpecLoadError, load_registry
from src.spec.validator import has_blocking_issues, validate_registry


REQUIRED_WORKFLOWS = {
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

FORBIDDEN_CONTRACTS = (
    ".claude/skills",
    "Claude 分析",
    "全部7只",
    "生成两份日报",
    "data/{code}/regime.json",
    "strategy_*.json",
    "tracking/daily/market/YYYY-MM-DD.md",
    "tracking/{code}-{name}/YYYY-MM-DD-analysis.md",
    "core: 3-5",
    "key: 2-3",
    "watch: 1-2",
)


def _live_documents(repo_root: Path) -> tuple[Path, ...]:
    fixed = (
        repo_root / "AGENTS.md",
        repo_root / "tracking/README.md",
        repo_root / "strategies/README.md",
        repo_root / "src/README.md",
        repo_root / "references/README.md",
    )
    scenarios = tuple(sorted((repo_root / "references/scenarios").glob("*.md")))
    skills = tuple(sorted((repo_root / ".agents/skills").glob("*/SKILL.md")))
    return fixed + scenarios + skills


def _legacy_contract_hits(repo_root: Path) -> tuple[str, ...]:
    hits = []
    for path in _live_documents(repo_root):
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_CONTRACTS:
            if phrase in text:
                hits.append(
                    f"{path.relative_to(repo_root)}: forbidden contract {phrase!r}"
                )
    return tuple(hits)


def _unregistered_skills(registry, repo_root: Path) -> tuple[str, ...]:
    actual = {
        path.parent.name
        for path in (repo_root / ".agents/skills").glob("*/SKILL.md")
    }
    return tuple(sorted(actual.symmetric_difference(registry.skills)))


def _incomplete_workflows(registry) -> tuple[str, ...]:
    incomplete = []
    for workflow_id in REQUIRED_WORKFLOWS:
        workflow = registry.workflows.get(workflow_id)
        if workflow is None:
            continue
        if not all(
            (
                workflow.outputs,
                workflow.policies,
                workflow.steps,
                workflow.completion,
                workflow.on_failure,
            )
        ):
            incomplete.append(workflow_id)
    return tuple(sorted(incomplete))


def main(repo_root: Path = ROOT) -> int:
    repo_root = Path(repo_root).resolve()
    try:
        registry = load_registry(repo_root / "spec")
        issues = validate_registry(registry, repo_root)
        skill_mismatches = _unregistered_skills(registry, repo_root)
        legacy_hits = _legacy_contract_hits(repo_root)
        workflow_mismatches = set(registry.workflows) != REQUIRED_WORKFLOWS
        incomplete_workflows = _incomplete_workflows(registry)
        if (
            has_blocking_issues(issues)
            or skill_mismatches
            or legacy_hits
            or workflow_mismatches
            or incomplete_workflows
        ):
            for issue in issues:
                if issue.severity == "block":
                    print(
                        f"{issue.code}: {issue.message} ({issue.location})",
                        file=sys.stderr,
                    )
            for skill_id in skill_mismatches:
                print(f"skill registration mismatch: {skill_id}", file=sys.stderr)
            for hit in legacy_hits:
                print(hit, file=sys.stderr)
            if workflow_mismatches:
                missing = sorted(REQUIRED_WORKFLOWS - set(registry.workflows))
                extra = sorted(set(registry.workflows) - REQUIRED_WORKFLOWS)
                print(
                    f"workflow registration mismatch: missing={missing}, extra={extra}",
                    file=sys.stderr,
                )
            for workflow_id in incomplete_workflows:
                print(f"incomplete workflow contract: {workflow_id}", file=sys.stderr)
            return 1

        generate_documents(registry, repo_root, check=True)

        print("specification valid")
        print("generated documentation current")
        print("11 workflows registered")
        return 0
    except (GeneratedSectionError, SpecLoadError, OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
