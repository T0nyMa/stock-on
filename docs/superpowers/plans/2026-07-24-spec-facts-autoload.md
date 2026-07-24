# Spec Facts Auto-Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make daily and weekly spec checks automatically consume committed, workflow-scoped structured facts while preserving strict gates.

**Architecture:** Add a focused `src/spec/facts.py` loader/validator and merge its result in the CLI before calling the existing gate engine. Store one committed JSON record per workflow under `data/spec/workflow-facts/`; existing gates remain responsible for evidence, decision, artifact, Git, and deployment validation.

**Tech Stack:** Python 3, JSON, pytest, existing `src.spec` registry and gate engine.

## Global Constraints

- Explicit `--facts` values override durable values recursively.
- Missing durable facts preserve current blocking behavior.
- Malformed, unknown-key, or cross-workflow durable records fail closed.
- Markdown is not parsed to infer evidence or decisions.
- Existing gate schemas are not weakened.

---

### Task 1: Durable Facts Loader and CLI Auto-Load

**Files:**
- Create: `src/spec/facts.py`
- Modify: `src/spec/cli.py`
- Test: `tests/spec/test_cli.py`

**Interfaces:**
- Produces: `load_workflow_facts(repo_root: Path, workflow: str) -> dict[str, Any]`
- Produces: `merge_facts(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]`
- Consumes: `data/spec/workflow-facts/{workflow}.json`

- [ ] **Step 1: Write failing tests**

Add tests that create `data/spec/workflow-facts/sample.json`, invoke `main()` without `--facts`, and assert the captured facts were auto-loaded. Add a nested override test asserting explicit `git_pushed.deployment.verified` replaces the durable value while its URL remains.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/spec/test_cli.py`

Expected: auto-load assertions fail because CLI still passes `{}`.

- [ ] **Step 3: Implement minimal loader and merge**

Implement:

```python
def merge_facts(base, override):
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = merge_facts(merged[key], value)
        else:
            merged[key] = value
    return merged
```

Load the workflow JSON when it exists and merge explicit facts over it in `cli.main`.

- [ ] **Step 4: Verify GREEN**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/spec/test_cli.py`

Expected: all CLI tests pass.

- [ ] **Step 5: Commit**

Commit loader, CLI, and tests as `fix: auto-load durable workflow facts`.

### Task 2: Strict Record Validation and Position Expansion

**Files:**
- Modify: `src/spec/facts.py`
- Test: `tests/spec/test_workflow_facts.py`

**Interfaces:**
- Produces: strict workflow record validation before returning `facts`
- Record schema: `{"schema_version":"1.0","workflow":"daily-report","facts":{...}}`

- [ ] **Step 1: Write failing validation tests**

Test rejection of invalid JSON shape, unknown top-level keys, wrong schema version, workflow mismatch, non-object facts, and malformed `positions` entries. Test acceptance of valid `{code,name}` positions.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/spec/test_workflow_facts.py`

Expected: failures because record validation does not exist.

- [ ] **Step 3: Implement strict validator**

Require exactly `schema_version`, `workflow`, and `facts`; require version `1.0`; require matching workflow; require facts mapping; validate every positions item has exactly non-empty string `code` and `name`.

- [ ] **Step 4: Verify GREEN**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/spec/test_workflow_facts.py tests/spec/test_final_review_regressions.py`

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

Commit as `fix: validate workflow fact records`.

### Task 3: Register July 24 Daily and Weekly Completion Evidence

**Files:**
- Create: `data/spec/workflow-facts/daily-report.json`
- Create: `data/spec/workflow-facts/weekly-report.json`
- Test: `tests/spec/test_registered_report_facts.py`

**Interfaces:**
- Consumes: 2026-07-24 reports, four position files, authoritative URLs, concrete report actions, verified Pages URLs
- Produces: reproducible daily and weekly facts records

- [ ] **Step 1: Write failing integration tests**

Invoke the real CLI without `--facts` at `now=2026-07-24` through `check_workflow` using loaded durable facts. Assert both completion reports pass and all four position paths resolve.

- [ ] **Step 2: Verify RED**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/spec/test_registered_report_facts.py`

Expected: failures because durable report records are absent.

- [ ] **Step 3: Add exact structured records**

Record required entities, one material claim and verified dated source per entity, one typed decision per entity, four position manifests, published paths, and verified HTTPS deployment URL. Use report-specific entities so coverage is exact.

- [ ] **Step 4: Verify GREEN and workflow gates**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q tests/spec/test_registered_report_facts.py
PYTHONPATH=. .venv/bin/python -m src.spec check --workflow daily-report --phase completion
PYTHONPATH=. .venv/bin/python -m src.spec check --workflow weekly-report --phase completion
```

Expected: tests and both completion checks pass.

- [ ] **Step 5: Commit**

Commit as `fix: register report completion facts`.

### Task 4: Full Verification and Publication

**Files:**
- Modify only files required by failed verification.

**Interfaces:**
- Produces: pushed branch and verified Pages-compatible repository state.

- [ ] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
PYTHONPATH=. .venv/bin/python -m src.spec validate
git diff --check
```

Expected: all tests pass, validation has no blocking issues, diff check is clean.

- [ ] **Step 2: Re-run four target gates**

Run daily and weekly preflight and completion checks without `--facts`. Expected: all four commands return zero.

- [ ] **Step 3: Commit any verification-only correction**

Commit only if verification required a scoped correction.

- [ ] **Step 4: Push and merge**

Push `fix/spec-facts-autoload`, create a PR, merge remotely to avoid the dirty main checkout, and verify the merge commit.

- [ ] **Step 5: Verify clean remote behavior**

Run the completion checks from the feature worktree against the merged commit or a fresh detached worktree and confirm both return zero.
