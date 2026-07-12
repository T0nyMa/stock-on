"""Deterministic Markdown generation from the project specification registry."""

from pathlib import Path

from .models import SpecRegistry


class GeneratedSectionError(ValueError):
    """Raised when generated document markers or contents are invalid."""


def replace_generated_section(source: str, name: str, content: str) -> str:
    """Replace one named generated region without touching surrounding bytes."""
    begin = f"<!-- BEGIN GENERATED: {name} -->"
    end = f"<!-- END GENERATED: {name} -->"
    if source.count(begin) != 1 or source.count(end) != 1:
        raise GeneratedSectionError(
            f"generated section {name!r} requires exactly one begin/end marker pair"
        )
    begin_at = source.index(begin) + len(begin)
    end_at = source.index(end)
    if begin_at > end_at:
        raise GeneratedSectionError(f"generated section {name!r} markers are out of order")
    body = content if content.endswith("\n") else content + "\n"
    return source[:begin_at] + "\n" + body + source[end_at:]


def _cell(items: tuple[str, ...]) -> str:
    return "<br>".join(f"`{item}`" for item in items) if items else "—"


def render_routes(registry: SpecRegistry) -> str:
    lines = [
        "| Route ID | 用户意图 | Workflow | Skill | 优先级 |",
        "|---|---|---|---|---:|",
    ]
    for route_id in sorted(registry.routes):
        route = registry.routes[route_id]
        intents = "<br>".join(f"“{intent}”" for intent in route.intents)
        skill = f"`${route.skill}`" if route.skill else "—"
        lines.append(
            f"| `{route.id}` | {intents} | `{route.workflow}` | {skill} | {route.priority} |"
        )
    return "\n".join(lines) + "\n"


def render_skills(registry: SpecRegistry) -> str:
    lines = [
        "| Skill ID | 分类 | 路径 | Workflows | 排除范围 |",
        "|---|---|---|---|---|",
    ]
    for skill_id in sorted(registry.skills):
        skill = registry.skills[skill_id]
        lines.append(
            f"| `{skill.id}` | `{skill.category}` | `{skill.path}` | "
            f"{_cell(skill.workflows)} | {_cell(skill.excludes)} |"
        )
    return "\n".join(lines) + "\n"


def render_workflows(registry: SpecRegistry) -> str:
    lines = [
        "| Workflow ID | Skills | Inputs | Optional inputs | Outputs | Policies | Preflight | Steps | Completion | On failure |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for workflow_id in sorted(registry.workflows):
        workflow = registry.workflows[workflow_id]
        lines.append(
            f"| `{workflow.id}` | {_cell(workflow.skills)} | {_cell(workflow.inputs)} | {_cell(workflow.optional_inputs)} | "
            f"{_cell(workflow.outputs)} | {_cell(workflow.policies)} | {_cell(workflow.preflight)} | "
            f"{_cell(workflow.steps)} | {_cell(workflow.completion)} | {_cell(workflow.on_failure)} |"
        )
    return "\n".join(lines) + "\n"


def generate_documents(
    registry: SpecRegistry, repo_root: Path, check: bool = False
) -> tuple[Path, ...]:
    """Generate registered Markdown regions, or verify them in check mode."""
    repo_root = Path(repo_root)
    documents = (
        (repo_root / "AGENTS.md", "routes", render_routes(registry)),
        (
            repo_root / "references" / "skills-index.md",
            "skills",
            render_skills(registry),
        ),
        (
            repo_root / "references" / "generated" / "workflows.md",
            "workflows",
            render_workflows(registry),
        ),
    )
    changed: list[Path] = []
    rendered: list[tuple[Path, bytes]] = []
    for path, section, content in documents:
        try:
            source_bytes = path.read_bytes()
            source = source_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise GeneratedSectionError(f"cannot read generated document {path}: {exc}") from exc
        result = replace_generated_section(source, section, content).encode("utf-8")
        if result != source_bytes:
            changed.append(path)
            rendered.append((path, result))

    if check and changed:
        paths = ", ".join(str(path) for path in changed)
        raise GeneratedSectionError(f"generated documents are out of date: {paths}")
    for path, result in rendered:
        path.write_bytes(result)
    return tuple(changed)
