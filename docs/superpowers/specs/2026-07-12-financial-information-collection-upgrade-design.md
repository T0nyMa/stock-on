# Financial Information Collection Upgrade Design

**Date:** 2026-07-12  
**Target:** `$financial-report-analysis`

## Objective

Make information completeness and recency a hard prerequisite for financial-report conclusions. The Skill must collect a traceable evidence pack before analyzing, prioritize the latest operating and expectation changes, and downgrade its output when required current information is missing.

## Core Principle

Information collection precedes analysis. Search must seek a complete and contradictory evidence set, not materials that merely support an existing thesis. Historical filings establish long-term quality; recent filings, calls, forecasts, regulation, media analysis, and market reactions identify current inflections.

## Two-Stage Workflow

### Stage A: Collection Only

Collect and index:

1. Latest official results, earnings preannouncement, preliminary results, corrections, and restatements.
2. Latest earnings call, management opening remarks, analyst Q&A, guidance, targets, and avoided questions.
3. Forecast revisions and earnings previews published in the most recent 90 days.
4. Regulatory disclosures, authoritative media analysis, industry developments, and material price-move catalysts from the most recent 90 days.
5. Five annual reports and their critical notes.
6. Comparable-period evidence for three to five peers.

Do not score or conclude during Stage A.

### Stage B: Analysis

Start only after the collection gate passes. Separate confirmed facts, management assumptions, analyst forecasts, media-sourced claims, interpretations, and open questions. When recent information contradicts the historical trend, explain the mechanism rather than averaging it away.

## Recency Priority

Use this order for the current state:

```text
latest official disclosure
→ latest earnings call
→ latest preannouncement / earnings preview / estimate revision
→ latest regulation and material event
→ five-year historical trend
```

Recency never overrides source authority. A recent rumor cannot override an audited filing; it is a current but weak signal requiring verification.

Every source receives:

- `event_date`
- `published_at`
- `retrieved_at`
- `freshness`: `current|recent|historical|stale`
- `evidence_class`
- `quality`
- `verification_status`

Freshness defaults:

- `current`: latest official reporting period or event within 30 days.
- `recent`: 31–90 days.
- `historical`: older than 90 days but still relevant to the five-year baseline.
- `stale`: superseded, corrected, or too old for the claim it supports.

## Mandatory Search Matrix

EasyAnySearch must be used to discover:

- Earnings-call transcripts and Q&A.
- Broker previews, consensus revisions, and forecast changes.
- Authoritative media interpretation and channel checks.
- Material price-move catalysts.
- Recent regulation, litigation, industry data, and peer developments.

Each category uses multiple Chinese and English queries. Discovery results must be followed to original company, exchange, SEC, regulator, broker, or a second independent source when possible.

## Collection Gate

A complete analysis requires:

- Five annual reports or an explicitly justified shorter history.
- Latest official report.
- Critical financial-statement notes.
- Segment data.
- Latest earnings call or an explicit `unavailable` result after documented search.
- Search for recent preannouncements, earnings previews, and forecast revisions.
- Search for recent regulatory/accounting events.
- At least two authoritative media sources for material current claims.
- Three peer comparisons, unless no valid peers exist and the limitation is documented.
- Resolved or explicitly logged core-data conflicts.

Hard missing items—latest official report, report version, reporting currency/unit, or unresolved core-statement conflict—block full analysis. Other missing items reduce coverage and force `stage_assessment` unless the Skill documents why the item is not applicable.

## Persistence

Add `financial_collection_status` alongside existing snapshots. It contains:

```json
{
  "schema_version": 1,
  "as_of": "2026-07-12",
  "company": {},
  "requirements": [],
  "sources": [],
  "gaps": [],
  "conflicts": [],
  "coverage_score": 0,
  "gate_status": "pass|partial|blocked",
  "allowed_output": "full_analysis|stage_assessment|collection_report"
}
```

The existing `financial_report_evidence` remains the analyzed evidence set; the new snapshot records whether collection was sufficient before analysis began.

## Report Changes

Every report begins with:

- Collection cutoff and latest reporting period.
- Coverage score and gate status.
- Current/recent sources used.
- Missing current information.
- Whether the output is full or provisional.

Add a “Recent Information and Expectation Changes” chapter before historical trend analysis. It distinguishes company guidance, analyst forecasts, media claims, and actual results, and lists the formal event that will confirm or refute each forecast.

## Integration

- `$deep-stock-analysis` consumes a financial summary only when collection gate is `pass`; otherwise it exposes the limitation.
- Daily/weekly reports use current and recent sources, not stale historical claims, and display pending forecast-verification events.
- Annual reports trigger a full collection refresh; ordinary quarterlies trigger an incremental refresh of latest report, call, estimates, regulation, media, peers, and market reaction.

## Testing

- Source freshness classification around 30/90-day boundaries.
- Latest version supersedes stale or corrected reports without deleting provenance.
- Missing latest report blocks full analysis.
- Missing call after documented search yields partial rather than pass.
- Recent weak media cannot override historical official fact.
- `financial_collection_status` validates and round-trips through SQLite and `src.data_access`.
- Skill contract requires EasyAnySearch, bilingual query matrix, collection gate, and provisional-output rules.

## Acceptance Criteria

- The Skill cannot enter scoring before collection gate evaluation.
- Recent information appears before five-year interpretation.
- Every current forecast is labeled and linked to a future verification event.
- Missing current information is visible rather than silently ignored.
- Collection status is persisted and readable by downstream workflows.
- Existing financial evidence and summary snapshots remain backward compatible.
