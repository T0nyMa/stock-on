# Task 9 report: Adopt stable IDs in core Skills

## Result

- Added a compact `## Project contract` section to all 11 requested core Skills.
- Each section uses only Workflow, Artifact, and Policy IDs registered in the current `spec/` registry.
- Preserved the existing research boundaries, evidence schemas, report templates, scoring methods, commands, and domain methodology.
- Added Skill contract regression coverage for the four representative orchestration Skills and all 11 updated core Skills.

## TDD evidence

- RED: `tests/spec/test_skill_contracts.py` failed on `daily-report` because the stable contract phrases were absent.
- GREEN: the focused contract suite passed after adding the registered contract sections (`2 passed`).

## Verification

- Focused contract and research suites: `21 passed`.
- All project Skill validators: `28` valid Skills.
- Spec suite: `96 passed`.
- Full suite: `194 passed`.
- `git diff --check`: clean.

The worktree does not contain its own `.venv`; verification used `/Users/majiang/Work/tools/stock-on/.venv/bin/python` against this worktree.
