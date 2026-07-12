# Task 4 report

## Status

Implemented the pre-Workflow project registry with real project paths, policies,
all current Skills, and formal artifacts. Routes intentionally remain empty for
Task 5.

## TDD evidence

- RED: `python -m pytest tests/spec/test_project_registry.py -v` collected three
  tests and failed all three because `spec/project.yaml` did not exist.
- Intermediate RED: after adding registry YAML, two tests passed and the static
  validation test failed on artifact references to not-yet-created workflows.
- GREEN: the validator now defers artifact/workflow cross-reference checks only
  when the Workflow registry is entirely empty. Existing validator contract tests
  confirm those checks remain active when workflows exist.

## Verification evidence

- `/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec -v`
  — 20 passed in 0.32s.
- `/Users/majiang/Work/tools/stock-on/.venv/bin/python -m src.spec validate`
  — exit 0, output `[]`.
- Registered Skill IDs exactly match the 28 directories containing
  `.agents/skills/*/SKILL.md`.

## Design notes

- Six mandatory policies are registered, including the exact AnySearch then
  EasyAnySearch fallback rule and material-fact verification gate.
- Sixteen formal artifacts are registered against the stable future Workflow
  IDs from the implementation plan.
- No Workflow or route definitions were added prematurely.

## Review corrections

- Replaced invented filesystem locations with actual storage contracts:
  `artifact.position` now uses `tracking/{code}-{name}/position.json`, and the
  published index uses repository-root `index.html`.
- Added `storage` and optional `kind` fields to `ArtifactSpec`; the loader remains
  backward-compatible by defaulting legacy records to `filesystem`.
- Registered bars, quote, fundamentals, news, indicators, research summary,
  financial collection status, and financial quality summary as
  `sqlite_data_access` records in `data/stock_analysis.db`, with the exact kinds
  supported by `src.data_access`.
- Added a direct staged-validation regression proving an entirely empty Workflow
  registry defers artifact reverse references, while adding one Workflow restores
  `ARTIFACT.UNKNOWN_PRODUCER` and `ARTIFACT.UNKNOWN_CONSUMER` checks.

### Review TDD and verification evidence

- RED: the new storage contract test failed because `artifact.position` was still
  `position.json`; the staged validator boundary test already passed and therefore
  documented the existing narrow behavior without requiring a validator change.
- Focused suite: 15 passed in 0.55s; static validation exited 0 with `[]`.
- Full spec suite: 22 passed in 1.08s.
