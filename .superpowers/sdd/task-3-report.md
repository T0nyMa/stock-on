# Task 3 Report: Intent resolver and inspect command

## Status

Implemented the intent resolver and `validate`/`inspect` CLI in the assigned worktree.

## TDD evidence

### RED

Command:

```bash
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec/test_router.py tests/spec/test_cli.py -v
```

Observed: collection failed with two expected `ModuleNotFoundError` errors for
`src.spec.router` and `src.spec.cli` before production code was added.

### GREEN

Focused command:

```bash
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec/test_router.py tests/spec/test_cli.py -v
```

Observed: `7 passed`.

Regression command:

```bash
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec -v
```

Observed: `17 passed`.

## Self-review

- Intent templates escape literal text and replace valid `{name}` placeholders
  with anchored, non-greedy named groups.
- Matching is deterministic: descending priority, then route ID; ties at the
  highest matched priority raise `AmbiguousRouteError`.
- Inspect output uses `ensure_ascii=False` and includes every requested field.
- Validate serializes all issues and returns exit status 1 when any issue blocks.
- Fixture route was updated to the placeholder form required by the task brief.

## Commit

Created with subject `feat: resolve project intents from specification`.
The final commit hash is included in the task handoff (embedding it here would
change the commit hash).

## Concerns

None. CLI defaults assume the repository-standard `spec/` directory and current
directory as repository root; both can be overridden for tests and tooling.
