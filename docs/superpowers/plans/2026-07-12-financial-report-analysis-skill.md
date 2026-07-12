# Financial Report Analysis Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `$financial-report-analysis` as a deterministic, evidence-backed financial-statement audit Skill and connect its SQLite summary to `$deep-stock-analysis`.

**Architecture:** The Skill orchestrates official filing collection and judgment; a focused Python analyzer validates normalized multi-year JSON and emits reproducible rule results, while a separate snapshot writer persists evidence and summaries through `MarketDataStore`. Existing deep research and reporting workflows consume the compact summary without repeating the five-year audit.

**Tech Stack:** Markdown Codex Skills, Python 3.12, SQLite/`MarketDataStore`, JSON, pytest, YAML.

## Global Constraints

- Default to five annual reports plus the latest interim report; extend to ten years for cyclical, acquisitive, capital-intensive, or anomalous companies.
- Official filings override structured data; preserve period, scope, currency, unit, URL, publication date, evidence class, and comparability.
- Never convert missing values to zero.
- Never output valuation, price targets, or trading/position instructions.
- Never allege fraud or misconduct without an official finding.
- Financial institutions must not use generic industrial-company rules.
- Preserve existing deep-analysis, strategy, daily, and weekly behavior.
- Leave the unrelated untracked `.codex/` directory untouched.

---

### Task 1: Skill Package Contract

**Files:**
- Create: `tests/test_financial_report_analysis_skill.py`
- Create: `.agents/skills/financial-report-analysis/SKILL.md`
- Create: `.agents/skills/financial-report-analysis/agents/openai.yaml`
- Create: `.agents/skills/financial-report-analysis/references/*.md`

**Interfaces:**
- Produces: discoverable `$financial-report-analysis` package and reference contract.

- [ ] Write a failing static test requiring the package, Phase 0–10, five-year default, consolidated/parent separation, evidence classes, comparability states, four-test issue cards, 15 domains, no-trade boundary, and every reference named in the design.
- [ ] Run `pytest -q tests/test_financial_report_analysis_skill.py`; expect missing-package failures.
- [ ] Initialize the package with Skill Creator using `--resources scripts,references` and valid UI metadata.
- [ ] Write concise orchestration in `SKILL.md`; put schemas, comparability, rules, scoring, issue cards, adapters, risk control, report structure, and gaps in focused references.
- [ ] Run the focused test and Skill Creator `quick_validate.py`; expect pass.

### Task 2: Normalized Financial Analyzer

**Files:**
- Create: `.agents/skills/financial-report-analysis/scripts/analyze_financials.py`
- Create: `tests/test_financial_analyzer.py`

**Interfaces:**
- Consumes: normalized JSON with `schema_version`, `company`, `periods`, `consolidated`, `parent`, `segments`, `nonfinancial_kpis`, `accounting_changes`, `audit_events`, `governance_events`, `sources`.
- Produces: `analyze(payload: dict) -> dict` containing `calculations`, `rules`, `clusters`, `gaps`, and `metadata`.

- [ ] Write failing tests for schema/unit/scope validation and chronological period normalization.
- [ ] Write failing tests proving missing values return `unavailable`, never zero or a false trigger.
- [ ] Write failing tests for receivables-vs-revenue, inventory-vs-revenue, cash-plus-debt, OCF-vs-profit, goodwill-vs-equity, capex-effectiveness, and rule clusters.
- [ ] Implement minimal pure functions `validate_payload`, `safe_ratio`, `growth`, `evaluate_rules`, `group_clusters`, and `analyze`, plus `--input/--output` CLI.
- [ ] Add industry override behavior that returns `not_applicable` for generic industrial rules when `industry_adapter=financial`.
- [ ] Run `pytest -q tests/test_financial_analyzer.py`; expect pass.

### Task 3: Financial Snapshot Persistence

**Files:**
- Create: `.agents/skills/financial-report-analysis/scripts/financial_snapshot.py`
- Modify: `src/data_access.py`
- Modify: `tests/test_data_access.py`
- Test: `tests/test_financial_report_analysis_skill.py`

**Interfaces:**
- Produces snapshot kinds `financial_report_evidence` and `financial_quality_summary`.
- Produces loaders `load_financial_report_evidence` and `load_financial_quality_summary`.

- [ ] Write failing tests for valid round trips, malformed evidence, malformed summary, invalid rating/severity/evidence class/comparability, and bare HK code lookup.
- [ ] Implement strict validation and a CLI matching the existing research snapshot writer pattern.
- [ ] Add both kinds to `src.data_access.query_payload` and CLI choices.
- [ ] Run focused snapshot and data-access tests; expect pass.

### Task 4: Integrate with Deep Research and Scenarios

**Files:**
- Modify: `.agents/skills/deep-stock-analysis/SKILL.md`
- Modify: `.agents/skills/deep-stock-analysis/references/integration-contract.md`
- Modify: `references/scenarios/first-time-setup.md`
- Modify: `.agents/skills/daily-report/SKILL.md`
- Modify: `.agents/skills/weekly-report/SKILL.md`
- Modify: `AGENTS.md`
- Test: `tests/test_financial_report_analysis_skill.py`

**Interfaces:**
- Consumes: latest `financial_quality_summary` in deep research Phase 4 and Phase 10.

- [ ] Add a failing integration-contract test for intent routing, deep-research consumption, material-event refresh, and incremental quarterly review.
- [ ] Add routes for “财报分析”, “财报深度解析”, “财报排雷”, and “财务质量”.
- [ ] Require deep research to load the summary and avoid repeating the five-year audit unless missing, stale, or materially invalidated.
- [ ] Make setup/reports refresh after annual reports, corrections, non-standard opinions, major M&A, regulatory findings, or material accounting changes; ordinary quarterlies use incremental comparison.
- [ ] Run focused tests; expect pass.

### Task 5: Forward Validation and Regression

**Files:**
- Modify as needed: `.agents/skills/financial-report-analysis/**`
- Modify: `docs/superpowers/plans/2026-07-12-financial-report-analysis-skill.md`

**Interfaces:**
- Validates transfer across resource, manufacturing/technology, healthcare, and platform companies.

- [ ] Exercise fixtures or normalized samples for 山东黄金, 工业富联, 恒瑞医药, and 阿里巴巴; verify distinct account questions and adapters.
- [ ] Confirm no output contains trading actions or unsupported fraud allegations.
- [ ] Run Skill Creator validation, focused tests, `pytest -q`, and `git diff --check`.
- [ ] Mark every plan checkbox complete, inspect status, and ensure `.codex/` is unstaged.
- [ ] Commit with `feat: add financial report analysis skill`.

