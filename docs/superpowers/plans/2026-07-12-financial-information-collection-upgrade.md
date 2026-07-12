# Financial Information Collection Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make recent, complete, traceable information collection a hard gate before `$financial-report-analysis` can issue full conclusions.

**Architecture:** Add a deterministic collection-status validator and SQLite snapshot, then update the Skill to run a bilingual EasyAnySearch discovery matrix before analysis. Downstream workflows consume gate status and expose provisional conclusions when coverage is incomplete.

**Tech Stack:** Markdown Codex Skills, Python 3.12, JSON, SQLite/`MarketDataStore`, pytest.

## Global Constraints

- Collection precedes analysis; no scoring before gate evaluation.
- Latest official disclosure and report version are mandatory for full analysis.
- Recent weak sources never override official evidence.
- Current/recent/historical/stale labels use 30/90-day boundaries.
- EasyAnySearch is mandatory for calls, estimates, media, catalysts, regulation, industry, and peers.
- Preserve existing snapshot and report compatibility.
- Leave `.codex/` untouched.

---

### Task 1: Collection Contract and Skill Workflow

**Files:**
- Modify: `.agents/skills/financial-report-analysis/SKILL.md`
- Create: `.agents/skills/financial-report-analysis/references/collection-protocol.md`
- Modify: `.agents/skills/financial-report-analysis/references/report-template.md`
- Modify: `tests/test_financial_report_analysis_skill.py`

- [ ] Write failing contract tests for collection-only Stage A, EasyAnySearch, bilingual queries, freshness, gate status, provisional outputs, latest-call/forecast/regulation/media/peer requirements.
- [ ] Run focused tests and confirm contract failure.
- [ ] Implement the recent-first workflow and report changes in Skill references.
- [ ] Run focused tests and Skill validation.

### Task 2: Deterministic Collection Status Validator

**Files:**
- Create: `.agents/skills/financial-report-analysis/scripts/collection_status.py`
- Create: `tests/test_financial_collection_status.py`

- [ ] Write failing tests for 30/90-day freshness boundaries, corrected-version staleness, missing latest-report blocking, missing call partial status, coverage score, and allowed output.
- [ ] Implement `classify_freshness`, `validate_payload`, `evaluate_gate`, and JSON CLI.
- [ ] Verify current weak media remains a source item but cannot satisfy an official-report requirement.
- [ ] Run focused tests.

### Task 3: SQLite Persistence and Downstream Integration

**Files:**
- Modify: `.agents/skills/financial-report-analysis/scripts/financial_snapshot.py`
- Modify: `src/data_access.py`
- Modify: `tests/test_data_access.py`
- Modify: `.agents/skills/deep-stock-analysis/SKILL.md`
- Modify: `.agents/skills/daily-report/SKILL.md`
- Modify: `.agents/skills/weekly-report/SKILL.md`

- [ ] Write failing tests for `financial_collection_status` validation, HK round trip, and CLI access.
- [ ] Add snapshot kind and `load_financial_collection_status`.
- [ ] Require deep research to consume only pass-gated summaries; reports surface pending forecast-verification events.
- [ ] Run focused tests.

### Task 4: Full Verification and Merge

**Files:**
- Modify: `docs/superpowers/plans/2026-07-12-financial-information-collection-upgrade.md`

- [ ] Run Skill validation, focused tests, full `pytest -q`, and `git diff --check`.
- [ ] Mark plan complete and commit `feat: require recent-first financial collection`.
- [ ] Merge locally to main, rerun full verification, and clean the owned worktree.

