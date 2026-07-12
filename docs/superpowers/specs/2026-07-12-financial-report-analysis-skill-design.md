# Financial Report Analysis Skill Design

**Date:** 2026-07-12  
**Status:** Approved direction; written-spec review pending  
**Skill:** `$financial-report-analysis`

## 1. Objective

Create an independent financial-report analysis Skill that determines whether a listed company's reported profit, assets, cash flows, and disclosures are sufficiently credible for further research. It is an upstream evidence provider for `$deep-stock-analysis`, not a valuation, price-target, trading, or position-decision workflow.

The Skill must combine the strongest ideas from `financial-red-flag-auditor-skill` with Stock-On's existing SQLite data layer, evidence schema, company-type adapters, report workflows, and research snapshots. It must not merely install or copy the external repository.

## 2. Scope and Default Research Window

Default evidence window:

- The most recent five annual reports.
- The latest interim or quarterly report.
- Audit reports, notes, restatements, inquiry replies, penalties, auditor changes, guarantees, pledges, related-party disclosures, and other material announcements in the same period.

Extend to ten years when the company is cyclical, acquisition-heavy, capital-intensive, subject to material accounting changes, or exhibits a multi-year anomaly. Use shorter windows only when the issuer has a shorter public history, and disclose the limitation.

## 3. Explicit Boundaries

The Skill may output:

- Financial-statement credibility and disclosure-quality conclusions.
- Deterministic red-flag results.
- Account-level analysis and P0/P1/P2/P3 issue cards.
- A 15-domain financial-quality score with deductions and uncertainty.
- Evidence gaps, falsification conditions, and next-report tracking items.
- A conclusion of `continue research`, `requires enhanced verification`, `information insufficient`, or `exclude from further research on financial-quality grounds`.

The Skill must not output:

- Buy, sell, hold, add, reduce, position size, entry price, stop, or target price.
- A valuation conclusion or price forecast.
- Allegations of fraud, false disclosure, tunneling, or misconduct unless an official regulator, court, exchange, auditor, or company correction has made that finding.
- A severe conclusion based only on a ratio, a single year, or third-party structured data.

## 4. Architecture

The Skill has four layers.

### 4.1 Filing Evidence Layer

Collect and index official filings, then normalize:

- Consolidated balance sheet, income statement, and cash-flow statement.
- Parent-company statements separately.
- Segment, geography, product, customer, capacity, production, and other nonfinancial KPIs.
- Notes for cash restrictions, receivables, inventory, fixed assets, construction in progress, goodwill, intangible assets, R&D, debt, guarantees, contingencies, related parties, taxes, and minority interests.
- Audit opinion, key audit matters, internal-control opinion, accounting changes, restatements, and corrections.

Official filings override SQLite vendor snapshots when values conflict. All core numbers retain unit, currency, period, scope, source URL, publication date, and evidence class.

### 4.2 Deterministic Screening Layer

A Python analyzer consumes normalized multi-year data and calculates reproducible trends and red-flag triggers. The first version covers these rule families:

- Revenue, receivables, contract assets, aging, and collection.
- Inventory growth, turnover, write-downs, cost, and gross margin.
- Cash authenticity, restricted cash, interest income, and debt coexistence.
- Net profit, recurring profit, operating cash flow, and free cash flow.
- Fixed assets, construction in progress, capex effectiveness, and impairment.
- Goodwill, acquisitions, long-term investments, and investment income.
- R&D capitalization, amortization, and product commercialization.
- Debt maturity, liquidity, financing dependence, and guarantees.
- Parent-consolidated divergence, minority interests, and trapped cash.
- Related parties, controller pledges, auditor/CFO changes, corrections, and regulatory findings.

Rule output is `triggered`, `not_triggered`, `unavailable`, or `not_comparable`. A rule hit starts an investigation; it does not establish wrongdoing. Root-cause-related hits must not be double-counted in scoring.

### 4.3 Interpretation and Risk-Control Layer

Before scoring, the agent must:

1. Understand the business model and relevant nonfinancial KPIs.
2. Check accounting-policy, estimate, standard, restatement, and presentation changes.
3. Build a comparability bridge or mark metrics `not_comparable`.
4. Apply the relevant market and industry adapter.
5. Reconcile core official values against SQLite or other structured data.

Every material issue must pass four tests:

- Business explanation: can price, volume, product mix, capacity, customer, geography, or industry cycle explain it?
- Accounting explanation: can recognition, estimate, classification, capitalization, impairment, tax, or consolidation explain it?
- Cash-flow test: did cash support or contradict the reported result?
- Asset-side trace: where did the profit, cash, or business claim land on the balance sheet?

Severe outcomes require a red-team review for benign explanations, corrected filings, double counting, source strength, and wording risk.

### 4.4 Synthesis and Integration Layer

Generate a long-form Markdown report plus two SQLite snapshots:

- `financial_report_evidence`: filing index, normalized facts, reconciliation log, comparability log, and rule results.
- `financial_quality_summary`: score, rating, source basis, hard gates, top issue cards, unresolved gaps, falsification items, reporting period, and source report.

`$deep-stock-analysis` reads the latest summary and uses it in financial quality, governance, capital-allocation, and falsification analysis. It must not independently repeat the full five-year accounting audit unless the summary is missing, stale, or materially invalidated.

## 5. Skill Package

```text
.agents/skills/financial-report-analysis/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── analyze_financials.py
│   └── financial_snapshot.py
└── references/
    ├── evidence-schema.md
    ├── normalization-contract.md
    ├── accounting-comparability.md
    ├── deterministic-rules.md
    ├── scoring-system.md
    ├── issue-card-playbook.md
    ├── risk-control.md
    ├── market-adapters.md
    ├── industry-adapters.md
    ├── report-template.md
    └── analysis-gaps.md
```

Detailed rules live in references, keeping `SKILL.md` focused on orchestration, routing, gates, and completion requirements.

## 6. Workflow

### Phase 0: Preflight

- Resolve legal company name, ticker, market, fiscal year, currency, accounting standard, and audit standard.
- Read `tracking/`, existing research reports, and existing financial snapshots.
- Determine whether five or ten years are required.

### Phase 1: Evidence Pack

- Retrieve official reports and material announcements.
- Record original/revised/restated versions.
- Build a source index and evidence coverage table.

### Phase 2: Business Map

- Map products, revenue model, customers, suppliers, geography, capacity, production/sales volume, price, costs, and industry cycle.
- Select nonfinancial KPIs needed to validate financial trends.

### Phase 3: Normalize and Reconcile

- Normalize consolidated and parent statements separately.
- Preserve original units and scope.
- Reconcile core metrics against structured snapshots and record unresolved differences.

### Phase 4: Accounting Comparability

- Check policy, estimate, standard, error-correction, restatement, and presentation changes.
- Build bridges for affected line items or mark periods not comparable.

### Phase 5: Deterministic Screening

- Run supported red-flag rules.
- Produce reproducible formulas, values, periods, statuses, and evidence references.
- Group related rule hits by root cause.

### Phase 6: Account-Level Analysis

- Analyze cash, debt, receivables, contract assets, inventory, capex, fixed assets, construction in progress, goodwill, investments, R&D, taxes, impairments, nonrecurring items, and related-party balances as applicable.
- Apply the four-test structure to every material issue.

### Phase 7: Three-Statement Synthesis

- Connect income, cash flow, working capital, balance-sheet expansion, financing, and distributions.
- Explain whether growth is internally funded and whether profit converts to distributable cash.

### Phase 8: Hard Gates and Scoring

- Apply hard gates only after data and comparability validation.
- Score 15 domains on a 100-point scale.
- Explain every deduction, uncertainty, unavailable item, and anti-double-counting decision.

### Phase 9: Issue Cards and Red-Team Review

- Generate P0/P1/P2/P3 issue cards.
- Red-team all P0, D/E ratings, exclusion conclusions, and reputation-sensitive language.

### Phase 10: Report and Persist

- Write the report to `tracking/{code}-{name}/financial-analysis-YYYY-MM-DD.md`.
- Save evidence and summary snapshots through the existing `MarketDataStore`.
- Record newly discovered capability gaps.

## 7. Evidence Contract

Important claims retain:

```json
{
  "claim": "Receivables grew faster than revenue for two years",
  "evidence_class": "calculated_fact",
  "period": "2024FY-2025FY",
  "scope": "consolidated",
  "currency": "CNY",
  "unit": "million",
  "formula": "receivables_growth - revenue_growth",
  "source_type": "annual_report",
  "source": "2025 annual report",
  "published_at": "2026-03-11",
  "url": "https://...",
  "quality": "primary",
  "status": "verified",
  "comparability": "comparable"
}
```

Evidence classes are `confirmed_fact`, `calculated_fact`, `third_party_data`, `interpretation`, and `open_question`. Comparability is `comparable`, `adjusted`, `not_comparable`, or `unresolved`.

## 8. Deterministic Data Contract

The analyzer accepts normalized JSON rather than raw PDFs. Initial top-level fields:

```json
{
  "schema_version": 1,
  "company": {},
  "periods": [],
  "consolidated": {},
  "parent": {},
  "segments": {},
  "nonfinancial_kpis": {},
  "accounting_changes": [],
  "audit_events": [],
  "governance_events": [],
  "sources": []
}
```

The analyzer validates units, periods, scope, and required fields, then emits calculations and rule results. Missing inputs produce `unavailable`; the script never converts missing data to zero.

## 9. Scoring and Severity

Use 15 domains totaling 100 points:

1. Audit and disclosure credibility.
2. Accounting policy and estimate quality.
3. Business-financial consistency.
4. Parent-consolidated structure.
5. Cash and financial-asset quality.
6. Revenue, receivables, and contract assets.
7. Inventory, cost, and gross margin.
8. Long-term assets and capex effectiveness.
9. Goodwill, acquisitions, and investments.
10. Recurring profit quality.
11. Cash-flow and free-cash-flow resilience.
12. Debt, liquidity, and financing dependence.
13. Working-capital efficiency.
14. Governance, related parties, guarantees, and litigation.
15. Earnings-management pattern risk.

Ratings are A/B/C/D/E. P0 means a critical reliability or solvency issue supported by official or multi-source evidence; P1 materially affects the financial-quality conclusion; P2 requires meaningful verification; P3 is a monitoring item. Thresholds are investigation defaults and must be overridden by industry economics when appropriate.

## 10. Market and Industry Adapters

Market adapters cover:

- A-share/CAS.
- Hong Kong/HKFRS or IFRS.
- US/US GAAP.
- A+H reconciliation.
- Chinese ADR/VIE-specific disclosure.

Industry adapters cover at minimum:

- Resource and cyclical mining.
- Manufacturing and hardware.
- Technology/software/platform.
- Consumer and retail.
- Healthcare and biotech.
- Banks, insurers, and brokers.
- Real estate, construction, utilities, and infrastructure.

Financial institutions must use industry-specific balance-sheet and cash-flow logic rather than industrial-company receivable, inventory, or operating-cash-flow rules.

## 11. Report Structure

1. Core conclusion and research-continuation judgment.
2. Evidence coverage and validation log.
3. Business map and applicable adapters.
4. Accounting comparability.
5. Five-year core financial trends.
6. Deterministic rule results.
7. Balance-sheet account analysis.
8. Income-statement account analysis.
9. Cash-flow account analysis.
10. Parent-consolidated and minority-interest analysis.
11. Governance and related-party analysis.
12. Three-statement synthesis.
13. Issue cards.
14. Hard gates and 15-domain score.
15. Red-team conclusion, unresolved questions, falsification, and next-report checklist.
16. Sources, formulas, and limitations.

Markdown is the required initial output. HTML and PDF are optional downstream formats and are outside the first implementation unless explicitly requested later.

## 12. Existing-System Integration

Required changes:

- Add AGENTS.md routing for “财报分析”, “财报深度解析”, “财报排雷”, and “财务质量”.
- Extend `src.data_access` to expose `financial_report_evidence` and `financial_quality_summary`.
- Update `$deep-stock-analysis` to load `financial_quality_summary` in Phase 4 and Phase 10.
- Update first-time setup to require a current financial summary when official financial reports have materially changed.
- Let daily and weekly reports read summary changes but never run a five-year audit on every report cycle.

Freshness policy:

- Re-run after annual reports, material restatements/corrections, non-standard audit opinions, major acquisitions/disposals, regulatory findings, or major accounting-policy changes.
- For ordinary quarterly reports, run an incremental review against the last annual baseline.

## 13. Error Handling

- Inaccessible filing: attempt another official exchange/company mirror; otherwise record a blocking evidence gap.
- Conflicting official versions: prefer the latest corrected/restated version and preserve the reconciliation trail.
- Unit or currency ambiguity: stop calculations for the affected metric and mark unresolved.
- Missing account note: return unavailable, never zero.
- Financial institution detected without adapter: stop generic scoring and require the financial-industry adapter.
- Severe conclusion without sufficient evidence: downgrade severity and wording.

## 14. Testing Strategy

### Contract Tests

- Required Skill files, routing, phases, evidence classes, output boundaries, and integration references.

### Analyzer Unit Tests

- Multi-year growth and ratio calculations.
- Missing values remain unavailable.
- Unit and scope validation.
- Receivable/revenue, inventory/revenue, cash/debt, OCF/profit, goodwill/equity, and capex rules.
- Cluster grouping and no double counting.
- Market/industry overrides.

### Snapshot Tests

- Evidence and summary validation and SQLite round trips.
- Bare Hong Kong code compatibility.
- `src.data_access` CLI access.

### Forward Tests

- 山东黄金: low-margin purchased gold, perpetual-bond interest, minority profit, capex, and mining cost gaps.
- 工业富联: receivables, inventory, cash conversion, customer concentration, and AI capex cycle.
- 恒瑞医药: R&D treatment, pipeline evidence, impairment, and commercialization.
- 阿里巴巴: segments, SBC, investments, buybacks, and market/accounting adapter.

No forward test may produce a trading action or unsupported fraud allegation.

## 15. Acceptance Criteria

- `$financial-report-analysis` is discoverable and passes Skill validation.
- Default workflow uses five annual reports plus the latest interim report.
- Official and structured values are reconciled and conflicts are visible.
- Consolidated and parent-company data are separated.
- Accounting comparability is checked before anomaly scoring.
- Deterministic rules are reproducible and missing values are not treated as zero.
- Material issues use the four-test issue-card structure.
- Fifteen-domain scoring explains deductions and avoids double counting.
- Financial evidence and summary snapshots round-trip through SQLite and `src.data_access`.
- `$deep-stock-analysis` consumes the summary without duplicating the full audit.
- Full regression tests pass and existing report/strategy behavior remains compatible.

## 16. Deferred Work

- Automated PDF filing download and table extraction.
- OCR for scanned reports.
- Standalone HTML/PDF export and browser visual QA.
- Proprietary data-vendor integrations.
- Fully automated peer selection.
- Investment timing or position decisions.
