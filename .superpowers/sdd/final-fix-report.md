# Final Whole-Branch Review Fix Report

Date: 2026-07-12  
Review baseline: `9c5d95c54891018fb41df2638091f480c1778adf`  
Implementation commit: `b1ae5c9fda122102c669ee8950f1a1168180cdfd`

## Outcome

All C1/C2, I1-I5, and M1/M2 findings are addressed without lowering gate severity or acceptance criteria.

- C1: implemented and registered `source_verification`, `decision_fields`, and `test_verification`; static validation and the final project checker now reject unknown evaluators.
- C2: daily/weekly completion explicitly requires applicable position artifacts and published HTML. Publication facts require a verified HTTPS URL; Git checks include applicable position paths, committed paths, zero ahead commits, and proof that `HEAD` is on the upstream branch.
- I1: added unique development, data-preparation, and quant-analysis routes with inspect coverage.
- I2: research/search gates require structured, dated, verified evidence and coverage of declared material claims and tracked entities.
- I3: freshness is a closed enum. Daily/trading-day/search/publish, weekly, current/incremental, and event/version-relative modes have explicit semantics; unknown values fail loading/static validation.
- I4: unresolved template fields produce specific blocking diagnostics; `positions` facts resolve and check every applicable position.
- I5: loader rejects unknown keys, wrong scalar types, invalid list elements, and invalid storage/freshness/missing/severity enums.
- M1: omitted `--phase` defaults to `all` and combines preflight and completion results.
- M2: generated workflow docs include optional inputs, preflight, steps, completion, and on-failure behavior.

## RED evidence

Initial regression command:

```text
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec/test_final_review_regressions.py -q
12 failed, 1 passed
```

The failures reproduced missing routes/evaluators, trivial URL false-pass, swallowed template fields, absent multi-position behavior, and permissive loader schemas. After the first implementation pass, the existing spec suite exposed two contract migrations (`source_links` structured facts and the formerly unknown minimal-fixture evaluator), confirming that old weak behavior was no longer accepted.

## GREEN evidence

```text
/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest tests/spec -q
127 passed in 9.72s

/Users/majiang/Work/tools/stock-on/.venv/bin/python -m pytest -q
225 passed in 19.32s

/Users/majiang/Work/tools/stock-on/.venv/bin/python scripts/check_project_spec.py
specification valid
generated documentation current
11 workflows registered

/Users/majiang/Work/tools/stock-on/.venv/bin/python -m src.spec validate
[]

/Users/majiang/Work/tools/stock-on/.venv/bin/python -m src.spec generate --check
{"changed": []}

git diff --check
(no output)
```

The repository's Skill validator is exercised by the full suite through `tests/test_financial_research_package.py`; both valid and invalid research-package contracts passed their expected assertions.

## Negative integration coverage

- Unknown configured evaluator makes `scripts/check_project_spec.py` fail without leaking success lines.
- A daily report with no deployment evidence blocks at `PUBLISH.PUSHED`.
- A daily report with verified deployment evidence but a dirty applicable `position.json` blocks at `PUBLISH.PUSHED`.
- Partial entity evidence, malformed/undated evidence, unresolved artifact parameters, and invalid YAML schemas block.

## Concerns

No release-blocking concern remains. Event-relative freshness callers must supply `freshness.<artifact_id>.current_version` and `latest_version`; this is intentional evidence, not an implicit filesystem-age fallback. Daily/weekly/deploy completion callers must likewise supply structured deployment and position facts.

## Re-review remediation

The updated re-review identified three additional false-pass boundaries. They are closed as follows:

- Evidence completeness targets now come only from independent top-level run facts: non-empty `required_entities` and non-empty `claim_manifest`. The gate-local payload accepts only `evidence` records and cannot redefine or under-report its target. Every material manifest claim and required entity must be covered.
- Decision completeness uses the same independent `required_entities`. Entity, trigger, and invalidation are non-empty strings; shares are positive integers excluding booleans; price is either a positive finite number or a positive finite ordered two-number range. Containers, booleans, NaN, infinity, zero, negatives, reversed ranges, and nonnumeric ranges block.
- Every allowed optional `project.yaml` field has an explicit shape. Timezones must resolve through `ZoneInfo`; principles are lists of non-empty strings; runtime is a closed mapping of `python`, `virtualenv`, and `test_command` to non-empty strings; ownership/owners are string-to-non-empty-string mappings. Unknown top-level and runtime keys block.

Re-review RED evidence:

```text
pytest tests/spec/test_final_review_regressions.py -q
25 failed, 21 passed
```

Re-review GREEN evidence:

```text
pytest tests/spec -q
156 passed in 8.62s

pytest -q
254 passed in 18.73s

scripts/check_project_spec.py
specification valid
generated documentation current
11 workflows registered
```
