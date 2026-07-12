# Task 6 Report: Deterministic documentation generator

## Status

Implemented a deterministic Markdown generator backed by `SpecRegistry`, added the `generate [--check]` CLI, migrated `AGENTS.md` and `references/skills-index.md` to manual plus generated regions, and added the workflow quick reference.

## TDD evidence

- RED: `tests/spec/test_generator.py` failed during collection with `ModuleNotFoundError: No module named 'src.spec.generator'`.
- GREEN: focused generator suite passed, 6 tests.
- Regression: full spec suite passed, 69 tests.

## Verification

- `/Users/majiang/Work/tools/stock-on/.venv/bin/python -m src.spec generate --check`
- A second normal generation returned an empty `changed` list and left the generated-document diff hash unchanged.
- `git diff --check`

## Notes

- Generated rows are sorted by stable registry IDs.
- Named regions require exactly one ordered begin/end pair.
- Replacement preserves every byte outside the marker region.
- Check mode does not write files and reports stale documents through a non-zero CLI result.

## Review follow-up: CRLF preservation

- Root cause: `Path.read_text()` used universal-newline translation, converting CRLF manual regions to LF before the whole document was rewritten.
- Added a generator-level regression covering all three documents and comparing the exact byte prefixes and suffixes outside their markers.
- RED: the regression failed with `b'manual\nbytes\n' != b'manual\r\nbytes\r\n'`.
- Fix: documents are now read and written as bytes, with explicit UTF-8 decode/encode only around marker replacement. Generated bodies retain their deterministic LF representation while manual bytes remain unchanged.
