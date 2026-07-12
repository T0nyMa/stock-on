# Stock-On Project Specification Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular specification registry, deterministic compiler, documentation generator, and graded runtime gates for every core Stock-On workflow.

**Architecture:** YAML under `spec/` is the single source for machine-decidable routes, artifacts, skills, policies, workflows, and gates. A focused `src/spec/` Python package loads typed records, validates cross-references, generates marked documentation sections, resolves intents, and checks workflow state; analytical judgment remains in Skills and methodology Markdown.

**Tech Stack:** Python 3.12, PyYAML 6.x, dataclasses, argparse, pathlib, pytest, Markdown, YAML.

## Global Constraints

- Codex execution is the primary consumer; human-readable documentation remains supported.
- One mandatory rule has exactly one authoritative source and is referenced by stable ID elsewhere.
- Machine-decidable rules belong in YAML; financial, technical, company-type, and trading judgment stays in Skills or methodology Markdown.
- Gate severity is fixed as `block`, `warn`, or `info`; runtime code cannot downgrade it.
- Generated sections are deterministic and cannot be manually edited.
- Missing data remains `unavailable`; no workflow may silently substitute zero or weak evidence.
- AnySearch is the primary web-search provider; EasyAnySearch is fallback for quota exhaustion, service failure, or inadequate results; material facts return to first-party sources.
- Preserve the user's untracked `.codex/` directory and `.superpowers/` brainstorming artifacts.
- Run tests with `.venv/bin/python -m pytest`, not the `.venv/bin/pytest` entry point, so the repository root remains importable.

---

## Milestone 1: Specification Core

### Task 1: Typed registry loader

**Files:**
- Create: `src/spec/__init__.py`
- Create: `src/spec/models.py`
- Create: `src/spec/loader.py`
- Create: `tests/spec/test_loader.py`
- Create: `tests/spec/fixtures/minimal/project.yaml`
- Create: `tests/spec/fixtures/minimal/routes.yaml`
- Create: `tests/spec/fixtures/minimal/artifacts.yaml`
- Create: `tests/spec/fixtures/minimal/skills.yaml`
- Create: `tests/spec/fixtures/minimal/policies/core.yaml`
- Create: `tests/spec/fixtures/minimal/workflows/sample.yaml`

**Interfaces:**
- Consumes: `Path` pointing to a `spec/` directory containing the four registry files and nested policy/workflow YAML files.
- Produces: `load_registry(root: Path) -> SpecRegistry` and immutable records `RouteSpec`, `ArtifactSpec`, `SkillSpec`, `PolicySpec`, `GateSpec`, `WorkflowSpec`.

- [ ] **Step 1: Write failing loader tests**

```python
from pathlib import Path
import pytest
from src.spec.loader import SpecLoadError, load_registry

FIXTURE = Path(__file__).parent / "fixtures/minimal"

def test_load_registry_returns_typed_records():
    registry = load_registry(FIXTURE)
    assert registry.project["project"] == "stock-on-test"
    assert registry.routes["route.sample"].workflow == "sample"
    assert registry.workflows["sample"].outputs == ("artifact.output",)
    assert registry.gates["SAMPLE.READY"].severity == "block"

def test_duplicate_ids_fail(tmp_path):
    root = tmp_path / "spec"
    root.mkdir()
    (root / "project.yaml").write_text("schema_version: '1.0'\nproject: x\n")
    (root / "routes.yaml").write_text("- {id: route.x, intents: ['x'], workflow: w, priority: 1}\n- {id: route.x, intents: ['y'], workflow: w, priority: 2}\n")
    (root / "artifacts.yaml").write_text("[]\n")
    (root / "skills.yaml").write_text("[]\n")
    (root / "policies").mkdir(); (root / "workflows").mkdir()
    with pytest.raises(SpecLoadError, match="duplicate id: route.x"):
        load_registry(root)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_loader.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'src.spec'`.

- [ ] **Step 3: Implement immutable models and loader**

```python
# src/spec/models.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass(frozen=True)
class GateSpec:
    id: str
    severity: str
    check: str
    message: str
    remediation: str

@dataclass(frozen=True)
class RouteSpec:
    id: str
    intents: tuple[str, ...]
    workflow: str
    skill: str | None
    priority: int

@dataclass(frozen=True)
class ArtifactSpec:
    id: str
    path: str
    producer: str
    consumers: tuple[str, ...]
    freshness: str
    missing: str

@dataclass(frozen=True)
class SkillSpec:
    id: str
    path: str
    category: str
    workflows: tuple[str, ...]
    excludes: tuple[str, ...]

@dataclass(frozen=True)
class PolicySpec:
    id: str
    description: str
    gates: tuple[GateSpec, ...]

@dataclass(frozen=True)
class WorkflowSpec:
    id: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    policies: tuple[str, ...]
    skills: tuple[str, ...]
    steps: tuple[str, ...]
    preflight: tuple[str, ...]
    completion: tuple[str, ...]

@dataclass(frozen=True)
class SpecRegistry:
    root: Path
    project: dict[str, Any]
    routes: dict[str, RouteSpec]
    artifacts: dict[str, ArtifactSpec]
    skills: dict[str, SkillSpec]
    policies: dict[str, PolicySpec]
    workflows: dict[str, WorkflowSpec]
    gates: dict[str, GateSpec]
```

Implement `loader.py` with `yaml.safe_load`, explicit required-key checks, tuple normalization, duplicate detection across each namespace, and `SpecLoadError(ValueError)`. Reject unknown gate severities outside `{"block", "warn", "info"}`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/spec/test_loader.py -v`

Expected: all loader tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec tests/spec
git commit -m "feat: add typed specification registry"
```

### Task 2: Cross-reference and drift validator

**Files:**
- Create: `src/spec/validator.py`
- Create: `tests/spec/test_validator.py`
- Modify: `src/spec/__init__.py`

**Interfaces:**
- Consumes: `SpecRegistry` and repository root.
- Produces: `validate_registry(registry: SpecRegistry, repo_root: Path) -> tuple[ValidationIssue, ...]`; `ValidationIssue` has `code`, `severity`, `message`, and `location`.

- [ ] **Step 1: Write failing validation tests**

```python
from dataclasses import replace
from pathlib import Path
from src.spec.loader import load_registry
from src.spec.models import RouteSpec
from src.spec.validator import validate_registry

FIXTURE = Path(__file__).parent / "fixtures/minimal"

def test_unknown_workflow_and_skill_are_reported():
    registry = load_registry(FIXTURE)
    bad = replace(registry, routes={"route.bad": RouteSpec("route.bad", ("bad",), "missing", "missing-skill", 1)})
    codes = {issue.code for issue in validate_registry(bad, FIXTURE)}
    assert {"ROUTE.UNKNOWN_WORKFLOW", "ROUTE.UNKNOWN_SKILL"} <= codes

def test_duplicate_intent_at_same_priority_is_error():
    registry = load_registry(FIXTURE)
    routes = dict(registry.routes)
    routes["route.duplicate"] = RouteSpec("route.duplicate", ("sample {stock}",), "sample", "sample-skill", 10)
    bad = replace(registry, routes=routes)
    assert any(issue.code == "ROUTE.AMBIGUOUS" for issue in validate_registry(bad, FIXTURE))
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_validator.py -v`

Expected: import fails because `src.spec.validator` does not exist.

- [ ] **Step 3: Implement validation rules**

Implement `ValidationIssue` and checks for unknown Workflow/Skill/Policy/Artifact/Gate references, missing Skill paths, Artifact producer/consumer mismatches, workflow dependency cycles, duplicate intent templates at equal priority, unsupported schema versions, generated-marker pairing, and forbidden live-document references to `.claude/skills`.

Use this public interface:

```python
@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    location: str

def has_blocking_issues(issues: tuple[ValidationIssue, ...]) -> bool:
    return any(issue.severity == "block" for issue in issues)
```

- [ ] **Step 4: Verify GREEN and regression suite**

Run: `.venv/bin/python -m pytest tests/spec/test_loader.py tests/spec/test_validator.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec tests/spec
git commit -m "feat: validate specification references and drift"
```

### Task 3: Intent resolver and inspect command

**Files:**
- Create: `src/spec/router.py`
- Create: `src/spec/cli.py`
- Create: `src/spec/__main__.py`
- Create: `tests/spec/test_router.py`
- Create: `tests/spec/test_cli.py`

**Interfaces:**
- Consumes: raw user intent and `SpecRegistry`.
- Produces: `resolve_intent(text: str, registry: SpecRegistry) -> RouteMatch`; CLI `inspect --intent TEXT` emits JSON.

- [ ] **Step 1: Write failing router tests**

```python
from pathlib import Path
import pytest
from src.spec.loader import load_registry
from src.spec.router import AmbiguousRouteError, resolve_intent

FIXTURE = Path(__file__).parent / "fixtures/minimal"

def test_resolve_extracts_named_parameter():
    match = resolve_intent("sample 阿里巴巴", load_registry(FIXTURE))
    assert match.route_id == "route.sample"
    assert match.workflow == "sample"
    assert match.params == {"stock": "阿里巴巴"}

def test_no_match_returns_none():
    assert resolve_intent("unrelated", load_registry(FIXTURE)) is None
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_router.py tests/spec/test_cli.py -v`

Expected: import fails for `src.spec.router` and `src.spec.cli`.

- [ ] **Step 3: Implement resolver and CLI**

Convert `{name}` placeholders to non-greedy named regex groups, anchor the pattern, sort matches by descending priority, and raise `AmbiguousRouteError` when equal-priority routes match. Implement CLI subcommands `validate` and `inspect`; `validate` returns exit 1 on blocking issues, while `inspect` prints route, workflow, skills, policies, inputs, outputs, gates, and extracted params as UTF-8 JSON.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/spec/test_router.py tests/spec/test_cli.py -v`

Expected: all router and CLI tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec tests/spec
git commit -m "feat: resolve project intents from specification"
```

---

## Milestone 2: Registry Content and Generated Documentation

### Task 4: Register project, policies, skills, and artifacts

**Files:**
- Create: `spec/project.yaml`
- Create: `spec/routes.yaml`
- Create: `spec/artifacts.yaml`
- Create: `spec/skills.yaml`
- Create: `spec/policies/development.yaml`
- Create: `spec/policies/data-quality.yaml`
- Create: `spec/policies/search.yaml`
- Create: `spec/policies/research.yaml`
- Create: `spec/policies/decision.yaml`
- Create: `spec/policies/publishing.yaml`
- Create: `tests/spec/test_project_registry.py`

**Interfaces:**
- Consumes: actual repository paths and the stable IDs defined in the design specification.
- Produces: a complete valid registry for the real project before Workflow files are added.

- [ ] **Step 1: Write failing project-registry contract tests**

```python
from pathlib import Path
from src.spec.loader import load_registry
from src.spec.validator import validate_registry

ROOT = Path(__file__).parents[2]

def test_required_policies_and_search_order_are_registered():
    registry = load_registry(ROOT / "spec")
    assert {"DEV.CHANGE", "DATA.QUALITY", "SEARCH.PRIORITY", "RESEARCH.EVIDENCE", "DECISION.SEPARATION", "PUBLISH.COMPLETE"} <= set(registry.policies)
    search = registry.policies["SEARCH.PRIORITY"]
    assert "AnySearch" in search.description
    assert "EasyAnySearch" in search.description

def test_all_project_skill_directories_are_registered():
    registry = load_registry(ROOT / "spec")
    actual = {p.parent.name for p in (ROOT / ".agents/skills").glob("*/SKILL.md")}
    assert actual == set(registry.skills)

def test_registry_has_no_blocking_static_issues():
    registry = load_registry(ROOT / "spec")
    assert not [i for i in validate_registry(registry, ROOT) if i.severity == "block"]
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_project_registry.py -v`

Expected: fails because `spec/` does not exist.

- [ ] **Step 3: Add real registry YAML**

Register every current project Skill discovered under `.agents/skills/*/SKILL.md`. Register formal artifacts including `database.stock_analysis`, `snapshot.bars`, `snapshot.quote`, `snapshot.fundamentals`, `snapshot.news`, `snapshot.indicators`, `artifact.report_context`, `artifact.tracklist`, `artifact.position`, `artifact.research_summary`, `artifact.financial_collection_status`, `artifact.financial_quality_summary`, `artifact.daily_report`, `artifact.weekly_report`, `artifact.discovery_report`, and `artifact.published_html`.

Encode these mandatory search gates in `search.yaml`:

```yaml
id: SEARCH.PRIORITY
description: "Use AnySearch first; use EasyAnySearch after quota exhaustion, service failure, or inadequate results; verify material facts against first-party sources."
gates:
  - id: SEARCH.MATERIAL_FACT_VERIFIED
    severity: block
    check: source_verification
    message: Material current facts require dated first-party or authoritative corroboration.
    remediation: Re-run search and bind each material fact to a dated source URL.
```

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/spec/test_project_registry.py -v`

Expected: all registry contract tests pass.

- [ ] **Step 5: Commit**

```bash
git add spec tests/spec/test_project_registry.py
git commit -m "feat: register project policies skills and artifacts"
```

### Task 5: Register all core workflows and routes

**Files:**
- Create: `spec/workflows/development.yaml`
- Create: `spec/workflows/data-preparation.yaml`
- Create: `spec/workflows/quant-analysis.yaml`
- Create: `spec/workflows/strategy-analysis.yaml`
- Create: `spec/workflows/deep-research.yaml`
- Create: `spec/workflows/financial-report.yaml`
- Create: `spec/workflows/position-decision.yaml`
- Create: `spec/workflows/daily-report.yaml`
- Create: `spec/workflows/weekly-report.yaml`
- Create: `spec/workflows/discovery.yaml`
- Create: `spec/workflows/deploy.yaml`
- Modify: `spec/routes.yaml`
- Create: `tests/spec/test_workflow_contracts.py`

**Interfaces:**
- Consumes: Policy, Skill, and Artifact IDs from Task 4.
- Produces: eleven complete Workflow specs and unique intent routes.

- [ ] **Step 1: Write failing workflow coverage tests**

```python
from pathlib import Path
from src.spec.loader import load_registry
from src.spec.router import resolve_intent

ROOT = Path(__file__).parents[2]
EXPECTED = {"development", "data-preparation", "quant-analysis", "strategy-analysis", "deep-research", "financial-report", "position-decision", "daily-report", "weekly-report", "discovery", "deploy"}

def test_all_core_workflows_are_registered():
    registry = load_registry(ROOT / "spec")
    assert EXPECTED <= set(registry.workflows)
    for workflow_id in EXPECTED:
        workflow = registry.workflows[workflow_id]
        assert workflow.policies
        assert workflow.steps
        assert workflow.outputs

def test_representative_intents_have_unique_routes():
    registry = load_registry(ROOT / "spec")
    assert resolve_intent("日报", registry).workflow == "daily-report"
    assert resolve_intent("财报分析 阿里巴巴", registry).workflow == "financial-report"
    assert resolve_intent("深度分析 山东黄金", registry).workflow == "deep-research"
    assert resolve_intent("建仓分析 002050", registry).workflow == "position-decision"
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_workflow_contracts.py -v`

Expected: missing workflow assertions fail.

- [ ] **Step 3: Add Workflow and route definitions**

For each Workflow, declare actual command or Skill steps, registered inputs/outputs, Policy IDs, preflight gates, completion gates, and failure behavior. The daily Workflow must depend on current report context, current-news verification, seven-section rendering, position update, commit, push, and deploy. Deep research and financial report Workflows must exclude trading outputs. Position decision must consume research summaries and produce price/share/trigger/invalidation instructions.

- [ ] **Step 4: Verify GREEN and static validation**

Run: `.venv/bin/python -m pytest tests/spec/test_workflow_contracts.py tests/spec/test_project_registry.py -v && .venv/bin/python -m src.spec validate`

Expected: tests pass and CLI exits 0.

- [ ] **Step 5: Commit**

```bash
git add spec tests/spec/test_workflow_contracts.py
git commit -m "feat: register core project workflows and routes"
```

### Task 6: Deterministic documentation generator

**Files:**
- Create: `src/spec/generator.py`
- Modify: `src/spec/cli.py`
- Modify: `AGENTS.md`
- Modify: `references/skills-index.md`
- Create: `references/generated/workflows.md`
- Create: `tests/spec/test_generator.py`

**Interfaces:**
- Consumes: `SpecRegistry` and files containing named generated markers.
- Produces: `generate_documents(registry: SpecRegistry, repo_root: Path, check: bool = False) -> tuple[Path, ...]`; CLI `generate [--check]`.

- [ ] **Step 1: Write failing generation tests**

```python
from pathlib import Path
from src.spec.generator import render_routes, replace_generated_section
from src.spec.loader import load_registry

ROOT = Path(__file__).parents[2]

def test_generated_routes_are_deterministic():
    registry = load_registry(ROOT / "spec")
    assert render_routes(registry) == render_routes(registry)
    assert "财报分析" in render_routes(registry)

def test_replace_generated_section_preserves_manual_text():
    source = "manual\n<!-- BEGIN GENERATED: routes -->\nold\n<!-- END GENERATED: routes -->\ntail\n"
    result = replace_generated_section(source, "routes", "new\n")
    assert result == "manual\n<!-- BEGIN GENERATED: routes -->\nnew\n<!-- END GENERATED: routes -->\ntail\n"
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_generator.py -v`

Expected: import fails because `src.spec.generator` does not exist.

- [ ] **Step 3: Implement generator and migrate entry documents**

Implement marker replacement that requires exactly one begin/end pair, preserves all manual text byte-for-byte outside markers, sorts rows by stable ID, and supports check-only mode. Shorten the manual section of `AGENTS.md` to project principle, invariant rules, precedence, directory navigation, and progressive-loading instructions. Generate route tables from `routes.yaml`; generate Skill tables from `skills.yaml`; generate Workflow summaries into `references/generated/workflows.md`.

- [ ] **Step 4: Verify deterministic output**

Run:

```bash
.venv/bin/python -m src.spec generate
git diff --exit-code -- AGENTS.md references/skills-index.md references/generated/workflows.md || true
.venv/bin/python -m src.spec generate --check
.venv/bin/python -m pytest tests/spec/test_generator.py -v
```

Expected: first generation updates documents; `generate --check` exits 0; tests pass; a second normal generation creates no new diff.

- [ ] **Step 5: Commit**

```bash
git add src/spec AGENTS.md references/skills-index.md references/generated/workflows.md tests/spec/test_generator.py
git commit -m "feat: generate project routing and skill documentation"
```

### Task 7: Remove stale documentation contracts

**Files:**
- Modify: `tracking/README.md`
- Modify: `strategies/README.md`
- Modify: `src/README.md`
- Modify: `references/README.md`
- Modify: relevant files under `references/scenarios/`
- Delete: scenario files proven unreferenced by `spec/routes.yaml` and all Skills
- Create: `tests/spec/test_legacy_references.py`

**Interfaces:**
- Consumes: generated Workflow summaries and Artifact registry.
- Produces: documentation with no live `.claude/skills`, obsolete two-file daily report, fixed stock-count, or JSON-first runtime contracts.

- [ ] **Step 1: Write failing legacy-reference scan**

```python
from pathlib import Path

ROOT = Path(__file__).parents[2]
LIVE = [ROOT / "AGENTS.md", ROOT / "tracking/README.md", ROOT / "strategies/README.md", ROOT / "src/README.md", ROOT / "references/README.md"] + list((ROOT / "references/scenarios").glob("*.md"))

def test_live_docs_have_no_obsolete_contracts():
    forbidden = (".claude/skills", "Claude 分析", "全部7只", "生成两份日报", "data/{code}/regime.json")
    hits = [(str(path), phrase) for path in LIVE for phrase in forbidden if phrase in path.read_text(encoding="utf-8")]
    assert hits == []
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_legacy_references.py -v`

Expected: assertion lists current stale references.

- [ ] **Step 3: Migrate documentation**

Replace duplicated procedures with links to `references/generated/workflows.md` and stable Policy/Artifact IDs. Keep methodology prose only where it adds professional judgment. Update strategy docs to `.agents/skills/strategy-*`, update tracking to the single-file seven-section daily contract, and update data docs to SQLite plus registered derived artifacts.

- [ ] **Step 4: Verify GREEN and generated-doc integrity**

Run: `.venv/bin/python -m pytest tests/spec/test_legacy_references.py -v && .venv/bin/python -m src.spec generate --check && .venv/bin/python -m src.spec validate`

Expected: all commands exit 0.

- [ ] **Step 5: Commit**

```bash
git add tracking/README.md strategies/README.md src/README.md references tests/spec/test_legacy_references.py
git commit -m "docs: migrate project guidance to specification registry"
```

---

## Milestone 3: Runtime Gates and Full Workflow Adoption

### Task 8: Gate evaluator and check command

**Files:**
- Create: `src/spec/gates.py`
- Modify: `src/spec/cli.py`
- Create: `tests/spec/test_gates.py`
- Create: `tests/spec/fixtures/gates/current.json`

**Interfaces:**
- Consumes: Workflow ID, phase, registry, repository root, current time/date, and optional JSON runtime facts.
- Produces: `check_workflow(...) -> CheckReport`; CLI JSON/text output and exit 1 only when a `block` gate fails.

- [ ] **Step 1: Write failing severity tests**

```python
from src.spec.gates import GateResult, CheckReport

def test_block_failure_fails_report_but_warning_does_not():
    blocked = CheckReport("daily-report", "preflight", (GateResult("A", "block", False, "expected", "actual", "fix"),))
    warned = CheckReport("daily-report", "preflight", (GateResult("B", "warn", False, "expected", "actual", "fix"),))
    assert blocked.ok is False
    assert warned.ok is True

def test_gate_result_serializes_required_diagnostics():
    result = GateResult("DATA.CURRENT", "block", False, "today", "yesterday", "run fetch")
    assert result.to_dict() == {"rule_id":"DATA.CURRENT","severity":"block","passed":False,"expected":"today","actual":"yesterday","remediation":"run fetch"}
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_gates.py -v`

Expected: import fails for `src.spec.gates`.

- [ ] **Step 3: Implement evaluator registry**

Implement deterministic evaluators for `path_exists`, `json_field`, `artifact_freshness`, `markdown_sections`, `source_links`, `git_commit_contains`, `git_pushed`, and `generated_docs_clean`. Unknown evaluator names are blocking configuration errors. Allow `--facts path.json` to inject external states such as deployment URL without embedding network operations in the checker.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/spec/test_gates.py tests/spec/test_cli.py -v`

Expected: all gate and CLI tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/spec tests/spec
git commit -m "feat: evaluate graded workflow gates"
```

### Task 9: Adopt stable IDs in core Skills

**Files:**
- Modify: `.agents/skills/daily-report/SKILL.md`
- Modify: `.agents/skills/weekly-report/SKILL.md`
- Modify: `.agents/skills/deploy/SKILL.md`
- Modify: `.agents/skills/deep-stock-analysis/SKILL.md`
- Modify: `.agents/skills/financial-report-analysis/SKILL.md`
- Modify: `.agents/skills/discovery/SKILL.md`
- Modify: `.agents/skills/screener/SKILL.md`
- Modify: `.agents/skills/sector-scan/SKILL.md`
- Modify: `.agents/skills/fetch-data/SKILL.md`
- Modify: `.agents/skills/tech-indicators/SKILL.md`
- Modify: `.agents/skills/decision-agent/SKILL.md`
- Create: `tests/spec/test_skill_contracts.py`

**Interfaces:**
- Consumes: stable Workflow, Policy, and Artifact IDs.
- Produces: Skill instructions that reference global contracts instead of duplicating them.

- [ ] **Step 1: Write failing Skill-contract test**

```python
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
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_skill_contracts.py -v`

Expected: missing stable-ID assertions fail.

- [ ] **Step 3: Update Skills without removing professional method**

Add a compact `## Project contract` section to each orchestration/data/research Skill with its Workflow ID, consumed Artifact IDs, produced Artifact IDs, and Policy IDs. Remove copied global search/deploy/data rules only after the stable references exist. Preserve domain-specific steps, templates, evidence schemas, and analysis boundaries.

- [ ] **Step 4: Validate all Skills and tests**

Run:

```bash
.venv/bin/python -m pytest tests/spec/test_skill_contracts.py tests/test_deep_stock_analysis_skill.py tests/test_financial_report_analysis_skill.py -v
for skill in .agents/skills/*; do test -f "$skill/SKILL.md" || continue; .venv/bin/python /Users/majiang/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill" || exit 1; done
```

Expected: tests pass and every project Skill validates.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills tests/spec/test_skill_contracts.py
git commit -m "docs: connect project skills to specification contracts"
```

### Task 10: End-to-end workflow checks and final migration gate

**Files:**
- Create: `tests/spec/test_end_to_end.py`
- Create: `scripts/check_project_spec.py`
- Modify: `spec/policies/development.yaml`
- Modify: `references/README.md`

**Interfaces:**
- Consumes: complete registry and representative fixture workspaces.
- Produces: one project command that validates schema, generated docs, legacy references, Skill registration, and all core Workflow contracts.

- [ ] **Step 1: Write failing end-to-end test**

```python
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]

def test_project_spec_check_passes():
    result = subprocess.run([sys.executable, "scripts/check_project_spec.py"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "specification valid" in result.stdout
    assert "generated documentation current" in result.stdout
    assert "11 workflows registered" in result.stdout
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/spec/test_end_to_end.py -v`

Expected: fails because `scripts/check_project_spec.py` does not exist.

- [ ] **Step 3: Implement the project check script**

The script must call library functions, not shell out recursively. It loads `spec/`, runs static validation, runs generator check mode, confirms all eleven required Workflow IDs, scans live docs for forbidden contracts, and prints exactly these success lines before exit 0:

```text
specification valid
generated documentation current
11 workflows registered
```

Document `.venv/bin/python scripts/check_project_spec.py` as the required development pre-commit verification in `development.yaml` and `references/README.md`.

- [ ] **Step 4: Run full verification**

Run:

```bash
.venv/bin/python scripts/check_project_spec.py
.venv/bin/python -m src.spec validate
.venv/bin/python -m src.spec generate --check
.venv/bin/python -m pytest -q
git diff --check
git status --short
```

Expected: project check prints three success lines; spec commands exit 0; full pytest reports zero failures; diff check emits nothing; status contains only intended changes plus the preserved untracked `.codex/` directory.

- [ ] **Step 5: Commit verification integration**

```bash
git add scripts/check_project_spec.py tests/spec/test_end_to_end.py spec/policies/development.yaml references/README.md
git commit -m "feat: enforce project specification integrity"
```

## Final Acceptance Checklist

- [ ] `inspect` resolves representative development, analysis, deep research, financial report, position decision, daily, weekly, discovery, and deploy intents uniquely.
- [ ] Every registered Artifact has a producer, consumers, freshness rule, and missing behavior.
- [ ] Every actual project Skill is registered and validates.
- [ ] `AGENTS.md` contains only manual invariants plus generated routing content; it no longer embeds the full daily procedure.
- [ ] Generated sections are deterministic and `generate --check` passes.
- [ ] Live documentation contains no obsolete Claude Skill paths, fixed stock counts, two-file daily contract, or JSON-first data instructions.
- [ ] All eleven Workflows declare inputs, outputs, policies, steps, gates, and failure behavior.
- [ ] Block failures stop a Workflow; warning and info results remain visible without changing completion truth.
- [ ] Full project tests and the project specification check pass with fresh output.
