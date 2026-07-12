# Evidence-First Financial Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable research folder and a data-rich, evidence-linked Alibaba financial analysis while upgrading the reusable financial-report skill.

**Architecture:** A deterministic validator enforces research-folder and report contracts. Source records and extracted tables live under a dated research directory; the narrative report consumes stable evidence IDs and follows a mandatory data-to-judgment structure.

**Tech Stack:** Markdown, JSON, CSV, Python 3, pytest, existing skill validation and SQLite snapshot tooling.

## Global Constraints

- Do not provide valuation or trading advice.
- Missing data is `unavailable`; irreconcilable metrics are `not_comparable`.
- Do not copy protected full text; store metadata, links, limited excerpts and summaries.
- Current claims require dated source links and official-source preference.
- Preserve the untracked `.codex/` directory.

---

### Task 1: Research-package contract and validator

**Files:**
- Create: `.agents/skills/financial-report-analysis/references/research-package.md`
- Create: `.agents/skills/financial-report-analysis/scripts/validate_research_package.py`
- Create: `tests/test_financial_research_package.py`
- Modify: `.agents/skills/financial-report-analysis/SKILL.md`
- Modify: `.agents/skills/financial-report-analysis/references/collection-protocol.md`
- Modify: `.agents/skills/financial-report-analysis/references/report-template.md`

**Interfaces:**
- Consumes: a research-directory path and report path.
- Produces: exit code 0 only when required folders, tables, report chapters and evidence references exist.

- [ ] Write tests that create incomplete temporary research folders and require failures for absent source index, tables, chapter sections, and evidence IDs.
- [ ] Run `pytest tests/test_financial_research_package.py -v` and verify the new tests fail because the validator does not exist.
- [ ] Implement the validator and the research-package reference contract.
- [ ] Update the skill, collection protocol, and report template to require extracted facts plus analysis chains rather than link-only coverage.
- [ ] Run `pytest tests/test_financial_research_package.py -v` and verify all focused tests pass.
- [ ] Commit with `feat: require evidence-first financial research packages`.

### Task 2: Alibaba evidence library and extracted tables

**Files:**
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/index.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/official/*.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/earnings-calls/*.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/estimates/*.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/media/*.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/regulatory/*.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/peers/*.md`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/tables/group-quarterly.csv`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/tables/segments.csv`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/tables/estimates.csv`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/tables/peers.csv`
- Create: `tracking/09988-阿里巴巴/research/2026-07-12/claims.json`

**Interfaces:**
- Consumes: official company, SEC/HKEX, call, analyst, regulatory, media and peer sources.
- Produces: stable evidence IDs and normalized tables consumed by the report.

- [ ] Collect official Alibaba FY2026 and five-quarter facts, including restated segment definitions and units.
- [ ] Collect the latest earnings-call prepared remarks and Q&A for cloud, quick commerce, AIDC, capex and cash flow.
- [ ] Collect recent analyst estimates with old/new values and formal validation events.
- [ ] Collect regulatory/media evidence and same-period peer metrics for Tencent, JD and Meituan, marking non-comparable fields.
- [ ] Build the source index, CSV tables and claim map; cross-check every material number against its source.
- [ ] Run the package validator and resolve all evidence-package failures.
- [ ] Commit with `research: build Alibaba financial evidence library`.

### Task 3: Data-rich Alibaba analysis

**Files:**
- Create: `tracking/09988-阿里巴巴/financial-analysis-2026-07-12-v2.md`
- Modify: `tracking/09988-阿里巴巴/financial-collection-status-2026-07-12.json`
- Modify: `tracking/09988-阿里巴巴/financial-quality-summary-2026-07-12.json`
- Modify: `tracking/09988-阿里巴巴/financial-report-evidence-2026-07-12.json`

**Interfaces:**
- Consumes: Task 2 evidence IDs and tables.
- Produces: one complete report whose material facts and judgments are traceable to the research library.

- [ ] Write all required report chapters with tables for five-quarter group trends and each major segment.
- [ ] For every core chapter, include data, calculated change, management explanation, external forecast, independent analysis, strongest counter-case and next-report validation.
- [ ] Separate confirmed results, management statements, third-party estimates and interpretation visually and semantically.
- [ ] Recalculate the collection gate and financial summary from the completed evidence library.
- [ ] Run the package validator against the v2 report and fix every reported failure.
- [ ] Commit with `research: rewrite Alibaba financial analysis with evidence chains`.

### Task 4: Full verification and documentation

**Files:**
- Modify only files required to correct verification failures introduced by Tasks 1–3.

**Interfaces:**
- Consumes: completed skill, validator, evidence library and report.
- Produces: verified repository state and documented test evidence.

- [ ] Run `pytest -q` and require zero failures.
- [ ] Run the project skill validator for `.agents/skills/financial-report-analysis` and require success.
- [ ] Run `python .agents/skills/financial-report-analysis/scripts/validate_research_package.py tracking/09988-阿里巴巴/research/2026-07-12 tracking/09988-阿里巴巴/financial-analysis-2026-07-12-v2.md` and require exit code 0.
- [ ] Review `git diff --check`, source dates, units, claim IDs and report boundaries.
- [ ] Commit any verification-only corrections with `fix: verify evidence-first financial analysis`.
