# Task 8 Report: graded gate evaluator and check command

## Delivered

- Added immutable `GateResult` and `CheckReport` diagnostics. Only failed `block`
  results make a report fail; failed warnings remain visible without changing the
  successful exit status.
- Added deterministic evaluators for `path_exists`, `json_field`,
  `artifact_freshness`, `markdown_sections`, `source_links`,
  `git_commit_contains`, `git_pushed`, and `generated_docs_clean`.
- Unknown evaluator names are reported as blocking configuration failures.
- Added `check --workflow ... --phase ...`, JSON and text renderers, `--facts`
  runtime-fact injection, and exit code 1 only for blocking failures (or invalid
  command/configuration input).
- Artifact checks honor storage contracts. `sqlite_data_access` checks query the
  logical snapshot kind (`stock_snapshots.kind`, with `stock_daily` for bars), so
  an unrelated row or an empty database cannot satisfy the artifact.

## TDD evidence

- RED: `test_gates.py` failed during collection with
  `ModuleNotFoundError: No module named 'src.spec.gates'`.
- GREEN: focused gate and CLI tests passed: `8 passed`.
- Regression: the complete specification suite passed: `82 passed`.

## Verification

Commands used:

```text
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec/test_gates.py tests/spec/test_cli.py -q
git diff --check
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec -q
```

The worktree does not expose its own `.venv` symlink, so verification used the
repository's shared virtual environment by absolute path.
