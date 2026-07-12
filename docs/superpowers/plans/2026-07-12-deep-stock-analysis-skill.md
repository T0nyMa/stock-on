# Deep Stock Analysis Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research-only `$deep-stock-analysis` Skill that combines the project's existing data, quantitative, strategy, news, and reporting capabilities into an evidence-backed company analysis framework that adapts by company type.

**Architecture:** Add an orchestration Skill above the existing SQLite data layer, Quantitative Analysis V2, market-regime router, strategy Skills, and web evidence search. Persist normalized research evidence and compact thesis summaries through the existing `stock_snapshots` interface, then let setup/position/report workflows consume those outputs without coupling deep research to trade timing.

**Tech Stack:** Markdown Codex Skills, Python 3, SQLite via `MarketDataStore`, pytest, YAML metadata.

## Global Constraints

- The Skill produces research conclusions, scenarios, falsification conditions, and evidence gaps; it must not output buy/sell/hold instructions, target entry prices, share counts, or stops.
- Reuse existing fetch, indicators, SQLite, Quant V2, market-regime, strategies, and EasyAnySearch capabilities. Do not duplicate indicator formulas or create another database.
- Preserve all existing strategy trading-mode outputs and report workflows.
- Current announcements, news, commodity prices, ownership, and regulatory facts require dated source links and preference for primary sources.
- Implement inline in this repository; project instructions do not authorize delegation.
- Leave the unrelated untracked `.codex/` directory untouched.

---

## Task 1: Add Contract Tests for the Skill Package

**Files:**
- Create: `tests/test_deep_stock_analysis_skill.py`
- Test: `tests/test_deep_stock_analysis_skill.py`

- [ ] Write a failing test that requires `.agents/skills/deep-stock-analysis/SKILL.md`, `agents/openai.yaml`, `scripts/research_snapshot.py`, the core references, seven adapter references, and the report template.
- [ ] Require `SKILL.md` to declare the research-only boundary, Phase 0–10 workflow, primary/secondary adapter limit, evidence quality labels, SQLite snapshot kinds, current-information sourcing, and no-trade-output rule.
- [ ] Require each adapter to contain driver, leading-indicator, valuation, risk, and falsification sections.
- [ ] Run `pytest -q tests/test_deep_stock_analysis_skill.py` and confirm failure because the package does not exist.

## Task 2: Scaffold and Specify `$deep-stock-analysis`

**Files:**
- Create: `.agents/skills/deep-stock-analysis/SKILL.md`
- Create: `.agents/skills/deep-stock-analysis/agents/openai.yaml`
- Create: `.agents/skills/deep-stock-analysis/references/core-framework.md`
- Create: `.agents/skills/deep-stock-analysis/references/integration-contract.md`
- Create: `.agents/skills/deep-stock-analysis/references/report-template.md`
- Create: `.agents/skills/deep-stock-analysis/references/analysis-gaps.md`

- [ ] Run the Skill Creator initializer with `--path .agents/skills --resources scripts,references` and remove only unused generated placeholders.
- [ ] Write concise trigger metadata and a default prompt explicitly naming `$deep-stock-analysis`.
- [ ] Define preflight reads: `tracking/tracklist.json`, matching tracking reports, `position.json` for context only, analysis methodology, SQLite snapshots, and the selected adapter references.
- [ ] Define deterministic Phase 0–10 execution, evidence schema, contradiction handling, thesis confidence, scenario rules, and output path `tracking/{code}-{name}/deep-analysis-YYYY-MM-DD.md`.
- [ ] Define integration boundaries for fetch/indicators, Quant V2, market-regime, strategy executor research mode, EasyAnySearch, and downstream reports.

## Task 3: Add Company-Type Adapters

**Files:**
- Create: `.agents/skills/deep-stock-analysis/references/resource-cycle.md`
- Create: `.agents/skills/deep-stock-analysis/references/technology-growth.md`
- Create: `.agents/skills/deep-stock-analysis/references/manufacturing.md`
- Create: `.agents/skills/deep-stock-analysis/references/consumer.md`
- Create: `.agents/skills/deep-stock-analysis/references/healthcare.md`
- Create: `.agents/skills/deep-stock-analysis/references/financial.md`
- Create: `.agents/skills/deep-stock-analysis/references/internet-platform.md`
- Test: `tests/test_deep_stock_analysis_skill.py`

- [ ] Specify routing signals and ambiguity handling; select at most one primary and one secondary adapter.
- [ ] For every adapter, define business drivers, leading indicators, moat questions, accounting traps, suitable valuation methods, scenario variables, key risks, and falsification conditions.
- [ ] Include example routing for Zijin Mining, Sanhua/NAURA, Hengrui, and Alibaba.
- [ ] Run the package contract tests and confirm adapter requirements pass.

## Task 4: Implement the Research Snapshot Writer with TDD

**Files:**
- Create: `.agents/skills/deep-stock-analysis/scripts/research_snapshot.py`
- Modify: `tests/test_deep_stock_analysis_skill.py`
- Reuse: `src/storage.py`

- [ ] Add failing tests for `research_evidence` and `research_summary` round trips through a temporary `MarketDataStore`.
- [ ] Add failing tests rejecting unsupported snapshot kinds, invalid evidence status/quality, missing claim/source/date fields, and malformed summary payloads.
- [ ] Add a failing test for bare Hong Kong code normalization compatibility.
- [ ] Implement a CLI accepting `--db`, `--code`, `--name`, `--market`, `--kind`, and `--input`, validating JSON before calling `MarketDataStore.save_snapshot`.
- [ ] Keep the payload JSON stable and include `schema_version`, `as_of`, and provenance fields.
- [ ] Run `pytest -q tests/test_deep_stock_analysis_skill.py` and confirm all snapshot tests pass.

## Task 5: Add Research Mode to Existing Strategy Interpretation

**Files:**
- Modify: `.agents/skills/strategy-executor/SKILL.md`
- Modify: `.agents/skills/market-regime/SKILL.md`
- Modify: `.agents/skills/deep-stock-analysis/references/integration-contract.md`
- Test: `tests/test_deep_stock_analysis_skill.py`

- [ ] Add a failing static contract test requiring `mode=trading|research` while preserving the current trading output contract.
- [ ] Define research mode as signal, score, evidence, uncertainty, invalidation, and market-interpretation output without action/position recommendations.
- [ ] Make market-regime document the research-mode routing path and its role as technical context rather than a business-quality conclusion.
- [ ] Run the focused tests and verify backward-compatible trading semantics remain documented.

## Task 6: Integrate Deep Research with Existing Methodology and Scenarios

**Files:**
- Modify: `references/analysis-methodology.md`
- Modify: `references/scenarios/first-time-setup.md`
- Modify: `references/scenarios/core-position.md`
- Modify: `.agents/skills/daily-report/SKILL.md`
- Modify: `.agents/skills/weekly-report/SKILL.md`
- Modify: `AGENTS.md`
- Test: `tests/test_deep_stock_analysis_skill.py`

- [ ] Split the methodology conceptually into reusable research core and downstream trading overlay.
- [ ] Make first-time setup require or generate a fresh deep-analysis summary before timing decisions.
- [ ] Make core-position, daily, and weekly workflows load the latest `research_summary`, compare thesis/falsification changes, and request a full rerun only for material events or periodic refresh.
- [ ] Add the intent route “深度分析 {code} / 深研 {code}” → `$deep-stock-analysis`.
- [ ] Preserve existing daily seven-chapter requirements and automatic deploy behavior.
- [ ] Run focused contract tests.

## Task 7: Validate the Skill and Four Archetypes

**Files:**
- Modify as needed: `.agents/skills/deep-stock-analysis/**`
- Test: `tests/test_deep_stock_analysis_skill.py`

- [ ] Run Skill Creator validation:
  `python /Users/majiang/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/deep-stock-analysis`
- [ ] Dry-run the workflow against Zijin Mining (resource-cycle), Sanhua or NAURA (manufacturing + technology-growth), Hengrui (healthcare), and Alibaba (internet-platform).
- [ ] Confirm each case produces distinct driver/valuation/risk/falsification questions and never emits trading actions.
- [ ] Record any missing project data capability in `references/analysis-gaps.md` instead of inventing facts.
- [ ] Re-run the focused test suite after corrections.

## Task 8: Full Regression and Documentation Verification

**Files:**
- Verify: all changed files

- [ ] Run `pytest -q` and retain the passing count.
- [ ] Run `git diff --check`.
- [ ] Inspect `git diff --stat` and `git status --short`; ensure `.codex/` is not staged.
- [ ] Verify existing report, strategy, storage, and Hong Kong alias tests still pass.
- [ ] Commit the implementation with a focused message such as `feat: add integrated deep stock analysis skill`.

