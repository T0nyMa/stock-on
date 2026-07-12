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
