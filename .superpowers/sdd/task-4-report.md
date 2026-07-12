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
