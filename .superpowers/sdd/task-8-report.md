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

## Review remediation

- `git_pushed` now proves three local Git conditions without mutation: every
  expected publication path is clean across worktree/index/untracked state,
  every expected path exists in `HEAD`, and `HEAD` has zero commits ahead of its
  upstream. Expected paths come from workflow output artifacts plus optional
  structured facts.
- `generated_docs_clean` separately inspects unstaged, staged, and untracked
  state for the three registered generated documents. Runtime facts may narrow
  the path list but cannot assert a truthy bypass.
- SQLite data-access freshness evaluates every required `facts.codes` entry (or
  `facts.params.code`) for the artifact's exact kind and reports each code's
  timestamp or missing state. Code lookup mirrors `MarketDataStore`'s HK alias
  behavior.
- Boolean runtime facts now require the JSON boolean type. Git evidence remains
  grounded in local read-only inspection; a `true` value cannot bypass it, while
  explicit false evidence blocks the gate.
- Filesystem mtimes, SQLite timestamps, and injected `now` values are normalized
  to the project timezone, defaulting to `Asia/Shanghai`; a UTC-day boundary
  regression test protects this contract.
- Evaluator exceptions are converted into deterministic blocking diagnostics.
  Tests now cover all eight evaluators, warn/info semantics, phase selection,
  CLI facts loading and malformed facts, and the reviewed false-pass cases.

Fresh post-review verification:

```text
tests/spec: 92 passed in 4.97s
full suite: 190 passed in 11.69s
git diff --check: clean
```

## Final review remediation

- Any evaluator exception now forces a blocking result even when the configured
  gate severity is `warn` or `info`; both severities have regression coverage
  proving `CheckReport.ok` becomes false.
- `generated_docs_clean` treats fact-provided paths as additions to the fixed
  registered generated-document set. Empty or narrowly scoped path lists can no
  longer hide a dirty default generated document.

Final fresh verification:

```text
focused gate/CLI tests: 20 passed in 2.71s
tests/spec: 94 passed in 7.45s
full suite: 192 passed in 15.83s
git diff --check and py_compile: clean
```
