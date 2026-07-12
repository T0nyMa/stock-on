"""Cross-reference and document-drift validation for project specifications."""

from dataclasses import dataclass
from pathlib import Path
import re

from .models import SpecRegistry


SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})
_MARKER = re.compile(r"<!--\s*(BEGIN|END) GENERATED:\s*([^>]+?)\s*-->")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    location: str


def has_blocking_issues(issues: tuple[ValidationIssue, ...]) -> bool:
    return any(issue.severity == "block" for issue in issues)


def validate_registry(
    registry: SpecRegistry, repo_root: Path
) -> tuple[ValidationIssue, ...]:
    """Return deterministic blocking issues for invalid references and drift."""
    issues: list[ValidationIssue] = []

    def add(code: str, message: str, location: str) -> None:
        issues.append(ValidationIssue(code, "block", message, location))

    version = str(registry.project.get("schema_version", ""))
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        add(
            "SCHEMA.UNSUPPORTED_VERSION",
            f"unsupported schema version: {version or '<missing>'}",
            "project.yaml:schema_version",
        )

    for route in registry.routes.values():
        location = f"routes.yaml:{route.id}"
        if route.workflow not in registry.workflows:
            add("ROUTE.UNKNOWN_WORKFLOW", f"unknown workflow: {route.workflow}", location)
        if route.skill is not None and route.skill not in registry.skills:
            add("ROUTE.UNKNOWN_SKILL", f"unknown skill: {route.skill}", location)

    seen_intents: list[tuple[str, str, int, str]] = []
    for route in registry.routes.values():
        for intent in route.intents:
            normalized = _normalize_intent(intent)
            raw = intent.casefold().strip()
            for previous_intent, previous_raw, previous_priority, previous_id in seen_intents:
                exact_equal_priority = (
                    normalized == previous_intent
                    and route.priority == previous_priority
                )
                template_overlap = (
                    normalized.startswith(previous_intent + " ")
                    or previous_intent.startswith(normalized + " ")
                    or (normalized == previous_intent and raw != previous_raw)
                )
                if exact_equal_priority or (
                    route.priority == previous_priority and template_overlap
                ):
                    add(
                        "ROUTE.AMBIGUOUS",
                        f"intent {intent!r} overlaps route {previous_id}",
                        f"routes.yaml:{route.id}",
                    )
            seen_intents.append((normalized, raw, route.priority, route.id))

    for skill in registry.skills.values():
        location = f"skills.yaml:{skill.id}"
        if not (Path(repo_root) / skill.path).is_file():
            add("SKILL.PATH_MISSING", f"skill path does not exist: {skill.path}", location)
        for workflow_id in skill.workflows:
            workflow = registry.workflows.get(workflow_id)
            if workflow is None:
                add("SKILL.UNKNOWN_WORKFLOW", f"unknown workflow: {workflow_id}", location)
            elif skill.id not in workflow.skills:
                add(
                    "SKILL.WORKFLOW_MISMATCH",
                    f"workflow {workflow_id} does not reference skill {skill.id}",
                    location,
                )

    for workflow in registry.workflows.values():
        location = f"workflows/{workflow.id}.yaml:{workflow.id}"
        for artifact_id in (*workflow.inputs, *workflow.outputs):
            if artifact_id not in registry.artifacts:
                add("WORKFLOW.UNKNOWN_ARTIFACT", f"unknown artifact: {artifact_id}", location)
        for policy_id in workflow.policies:
            if policy_id not in registry.policies:
                add("WORKFLOW.UNKNOWN_POLICY", f"unknown policy: {policy_id}", location)
        for skill_id in workflow.skills:
            skill = registry.skills.get(skill_id)
            if skill is None:
                add("WORKFLOW.UNKNOWN_SKILL", f"unknown skill: {skill_id}", location)
            elif workflow.id not in skill.workflows:
                add(
                    "WORKFLOW.SKILL_MISMATCH",
                    f"skill {skill_id} does not reference workflow {workflow.id}",
                    location,
                )
        for gate_id in (*workflow.preflight, *workflow.completion):
            if gate_id not in registry.gates and gate_id not in registry.artifacts:
                add("WORKFLOW.UNKNOWN_GATE", f"unknown gate: {gate_id}", location)

    # Artifact names may be registered one milestone before workflows. Once the
    # first workflow exists, enforce the complete bidirectional contract.
    if registry.workflows:
        for artifact in registry.artifacts.values():
            location = f"artifacts.yaml:{artifact.id}"
            producer = registry.workflows.get(artifact.producer)
            if producer is None:
                add(
                    "ARTIFACT.UNKNOWN_PRODUCER",
                    f"unknown producer: {artifact.producer}",
                    location,
                )
            elif artifact.id not in producer.outputs:
                add(
                    "ARTIFACT.PRODUCER_MISMATCH",
                    f"producer {artifact.producer} does not declare output {artifact.id}",
                    location,
                )
            for consumer_id in artifact.consumers:
                consumer = registry.workflows.get(consumer_id)
                if consumer is None:
                    add(
                        "ARTIFACT.UNKNOWN_CONSUMER",
                        f"unknown consumer: {consumer_id}",
                        location,
                    )
                elif artifact.id not in consumer.inputs:
                    add(
                        "ARTIFACT.CONSUMER_MISMATCH",
                        f"consumer {consumer_id} does not declare input {artifact.id}",
                        location,
                    )

    # Also enforce the workflow side of artifact producer/consumer contracts.
    for workflow in registry.workflows.values():
        for artifact_id in workflow.outputs:
            artifact = registry.artifacts.get(artifact_id)
            if artifact is not None and artifact.producer != workflow.id:
                add(
                    "ARTIFACT.PRODUCER_MISMATCH",
                    f"output {artifact_id} names {artifact.producer} as producer, not {workflow.id}",
                    f"workflows/{workflow.id}.yaml:{workflow.id}",
                )
        for artifact_id in workflow.inputs:
            artifact = registry.artifacts.get(artifact_id)
            if artifact is not None and workflow.id not in artifact.consumers:
                add(
                    "ARTIFACT.CONSUMER_MISMATCH",
                    f"input {artifact_id} does not name {workflow.id} as consumer",
                    f"workflows/{workflow.id}.yaml:{workflow.id}",
                )

    _validate_cycles(registry, add)
    _validate_live_documents(Path(repo_root), add)
    return tuple(issues)


def _validate_cycles(registry: SpecRegistry, add) -> None:
    graph: dict[str, set[str]] = {workflow_id: set() for workflow_id in registry.workflows}
    for artifact in registry.artifacts.values():
        if artifact.producer in graph:
            graph[artifact.producer].update(
                consumer for consumer in artifact.consumers if consumer in graph
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: tuple[str, ...]) -> None:
        if node in visiting:
            cycle = path[path.index(node) :] + (node,)
            add(
                "WORKFLOW.DEPENDENCY_CYCLE",
                f"workflow dependency cycle: {' -> '.join(cycle)}",
                f"workflows/{node}.yaml:{node}",
            )
            return
        if node in visited:
            return
        visiting.add(node)
        for successor in sorted(graph[node]):
            visit(successor, path + (successor,))
        visiting.remove(node)
        visited.add(node)

    for workflow_id in sorted(graph):
        visit(workflow_id, (workflow_id,))


def _normalize_intent(intent: str) -> str:
    return " ".join(re.sub(r"\{[^{}]+\}", "", intent.casefold()).split())


def _validate_live_documents(repo_root: Path, add) -> None:
    paths: list[Path] = []
    agents = repo_root / "AGENTS.md"
    if agents.is_file():
        paths.append(agents)
    references = repo_root / "references"
    if references.is_dir():
        paths.extend(sorted(references.rglob("*.md")))

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            add("DOC.READ_FAILED", f"cannot read live document: {exc}", str(path))
            continue
        relative = str(path.relative_to(repo_root))
        if ".claude/skills" in text:
            add(
                "DOC.FORBIDDEN_CLAUDE_SKILL",
                "live document references legacy .claude/skills",
                relative,
            )
        markers: dict[str, list[str]] = {}
        for kind, raw_name in _MARKER.findall(text):
            markers.setdefault(raw_name.strip(), []).append(kind)
        for name, kinds in markers.items():
            if kinds != ["BEGIN", "END"]:
                add(
                    "GENERATED.MARKER_UNPAIRED",
                    f"generated marker {name!r} is not one ordered BEGIN/END pair",
                    relative,
                )
