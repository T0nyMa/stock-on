"""Command-line interface for project specification inspection."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Sequence

from .loader import load_registry
from .generator import GeneratedSectionError, generate_documents
from .router import AmbiguousRouteError, resolve_intent
from .validator import has_blocking_issues, validate_registry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.spec")
    parser.add_argument("--spec-root", type=Path, default=Path("spec"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--intent", required=True)
    generate = commands.add_parser("generate")
    generate.add_argument("--check", action="store_true")
    return parser


def _emit(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _validate(spec_root: Path, repo_root: Path) -> int:
    issues = validate_registry(load_registry(spec_root), repo_root)
    _emit([asdict(issue) for issue in issues])
    return 1 if has_blocking_issues(issues) else 0


def _inspect(spec_root: Path, intent: str) -> int:
    registry = load_registry(spec_root)
    try:
        match = resolve_intent(intent, registry)
    except AmbiguousRouteError as exc:
        _emit({"error": str(exc)})
        return 1
    if match is None:
        _emit({"error": "no matching route"})
        return 1

    workflow = registry.workflows[match.workflow]
    _emit(
        {
            "route": match.route_id,
            "workflow": workflow.id,
            "skills": list(workflow.skills),
            "policies": list(workflow.policies),
            "inputs": list(workflow.inputs),
            "outputs": list(workflow.outputs),
            "gates": {
                "preflight": list(workflow.preflight),
                "completion": list(workflow.completion),
            },
            "params": match.params,
        }
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "validate":
        return _validate(args.spec_root, args.repo_root)
    if args.command == "generate":
        try:
            changed = generate_documents(
                load_registry(args.spec_root), args.repo_root, check=args.check
            )
        except GeneratedSectionError as exc:
            _emit({"error": str(exc)})
            return 1
        _emit({"changed": [str(path) for path in changed]})
        return 0
    return _inspect(args.spec_root, args.intent)
