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

## Review follow-up

- Replaced provider-conflicting EasyAnySearch mandates in the deep-research and financial-report Skills with the registered `SEARCH.PRIORITY` behavior: AnySearch first; EasyAnySearch only after quota exhaustion, service failure, or inadequate results; material facts verified against dated first-party sources.
- Scanned every live project Skill; no other EasyAnySearch mandates were present.
- Standardized contract blocks as ordered `Workflow`, `Policies`, `Consumes`, and `Produces` fields.
- Replaced phrase-presence assertions with a deterministic parser that loads `spec/` through `load_registry`, compares exact workflow policies/required inputs/outputs, and verifies both Skill-to-Workflow and Workflow-to-Skill registration links.
- Added negative coverage for extra/missing/swapped IDs and a broken reverse link.
- Follow-up focused suites: `25 passed`.
- Follow-up Skill validation: all `28` project Skills valid.
- Follow-up spec suite: `100 passed`.
- Follow-up full suite: `198 passed`.

## Final review follow-up

- Updated the deep-research integration contract and financial collection protocol to defer to `SEARCH.PRIORITY`, with AnySearch primary, EasyAnySearch limited to the registered fallback conditions, and dated first-party verification required for material facts.
- Added a recursive regression scan over every `.agents/skills/**/*.md` file for direct EasyAnySearch mandate patterns while allowing conditional fallback mentions.
- Final focused suites: `26 passed`.
- Final Skill validation: all `28` project Skills valid.
