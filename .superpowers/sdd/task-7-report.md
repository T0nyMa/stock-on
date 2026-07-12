# Task 7 Report — Remove stale documentation contracts

## Status

Completed documentation migration to the project specification registry.

## Changes

- Added `tests/spec/test_legacy_references.py` and observed the required RED failure against five live stale references before migration.
- Reworked `tracking/README.md`, `strategies/README.md`, `src/README.md`, and `references/README.md` around generated Workflow summaries and stable Artifact/Policy IDs.
- Migrated retained scenarios away from fixed strategy/candidate counts, per-strategy JSON-first procedures, and the unregistered regime sidecar.
- Preserved methodology prose, including peer comparison, evidence thresholds, scenario construction, and professional judgment.
- Deleted `references/scenarios/daily-summary.md` and `references/scenarios/weekly-summary.md` after exact-reference scans found no current route or Skill consumers. Their contracts are superseded by `daily-report`, `weekly-report`, the generated workflow reference, and the daily template.
- Kept `references/scenarios/discovery.md` because `.agents/skills/discovery/SKILL.md` directly references it; migrated it in place.

## Verification

- RED: `/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec/test_legacy_references.py -v` failed with the expected stale-reference assertion.
- GREEN: the same command passed (`1 passed`).
- `/Users/majiang/Work/tools/stock-on/.venv/bin/python -m src.spec generate --check` returned `{"changed": []}`.
- `/Users/majiang/Work/tools/stock-on/.venv/bin/python -m src.spec validate` returned `[]`.

## Concerns

- The task worktree has no local `.venv`; verification used the repository root virtual environment at `/Users/majiang/Work/tools/stock-on/.venv`.
- Historical implementation plans may still mention deleted scenario paths. They are archival documents, not live routes, Skills, or scenario guidance, and were intentionally preserved.

## Review follow-up

- Migrated `$daily-report` to one authoritative `artifact.daily_report` Markdown file while preserving all seven sections, named core-company depth, all-observation coverage, evidence rules, position updates, and automatic HTML deployment.
- Migrated `$deploy` so daily HTML is generated only from the registered daily report; removed independent market and per-stock report dependencies.
- Migrated `$market-regime` to consume `snapshot.indicators` and return an in-workflow classification without a sidecar.
- Migrated `$decision-agent` to consume the registered strategy aggregate, SQLite/report context, research, financial-quality, and discovery artifacts; it now only updates registered position-decision outputs when authorized.
- Replaced absolute strategy vote counts with normalized ratios plus weighted-score thresholds, and fixed discovery recommendation counts with evidence/score thresholds and tracking-capacity language.
- Restored stable `core` / `key` / `watch` semantics in `tracking/README.md`.
- Expanded the regression scan to every project Skill and added focused assertions for the four reviewed behaviors. The review RED run failed all four original behavior tests (plus the explicit registered-input assertion before implementation); the final focused run passed all five.

## Routed-Skill follow-up

- Migrated every `strategy-*` Skill from per-strategy sidecar writes to structured in-memory returns; analytical steps and result schemas remain intact. `$strategy-executor` is now the sole writer of `artifact.strategy_scan`.
- Added normalized buy/hold/sell ratios, weighted-score calculation, and variable-count verdict thresholds to `$strategy-executor`; raw counts are diagnostic only.
- Migrated `$discovery` from fixed L3/recommendation counts to evidence and score gates plus current tracking capacity, including valid empty recommendations.
- Migrated `$weekly-report` to consume only the week's registered single-file daily reports and current registered summaries.
- Strengthened regex/glob-aware regression coverage across every project Skill for unregistered strategy sidecars, split daily sources, fixed candidate counts, and raw-count-only verdict rules. The focused RED run failed on strategy sidecars and weekly split inputs before migration; the GREEN run passed all seven checks.
