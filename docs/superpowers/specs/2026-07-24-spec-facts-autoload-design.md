# Spec Facts Auto-Loading Design

## Goal

Make registered daily and weekly workflow checks succeed from durable project evidence without requiring operators to hand-build and pass a transient `--facts` JSON file.

## Problem

`python -m src.spec check` currently defaults to `facts={}`. Artifact gates can inspect registered files, but research, decision, position-template, and publication gates depend on structured facts supplied by the caller. The result is a false negative: reports, positions, concrete actions, commits, and verified Pages URLs may exist while the completion check reports that all four are missing.

The fix must not infer compliance by loosely parsing prose. Structured evidence remains mandatory.

## Architecture

Add a deterministic workflow-facts module under `src/spec/`. It loads a durable record from `data/spec/workflow-facts/{workflow}.json`, validates that the record targets the requested workflow, and merges it with explicit CLI facts. Explicit `--facts` values take precedence.

The durable record contains:

- `positions`: resolved `{code, name}` instances for every applicable open position;
- `required_entities` and `claim_manifest`;
- gate payloads for `source_links` and `source_verification`;
- typed `decision_fields.decisions`;
- `git_pushed.paths` and `git_pushed.deployment`;
- optional freshness facts needed by registered artifacts.

Daily and weekly report execution writes these records after evidence collection and after publication verification. The records are committed with the reports so checks are reproducible from a clean clone.

## CLI Behavior

`python -m src.spec check --workflow daily-report --phase completion`:

1. Loads the registered durable facts record when present.
2. Loads `--facts` when provided.
3. Deep-merges explicit facts over durable facts.
4. Runs existing gates without weakening their validation.

If no durable record exists, behavior remains blocked with the current diagnostics. Malformed or cross-workflow records fail closed with an explicit error.

## Position Resolution

Parameterized artifacts are never expanded from arbitrary directory scans. The `positions` array in the durable record is the completeness manifest. Each item must contain non-empty `code` and `name`; the existing artifact formatter resolves `tracking/{code}-{name}/position.json`.

This preserves deterministic completeness and prevents unrelated historical position files from silently entering a workflow.

## Evidence and Decision Records

The existing strict gate schemas remain unchanged:

- every material claim is declared in `claim_manifest`;
- every claim/entity pair has dated, verified evidence;
- each decision has an entity, positive price or price range, positive integer shares, trigger, and invalidation;
- all required entities are covered.

The facts writer records these structures directly from the workflow’s research and decision step. It does not extract them from Markdown.

## Publication Record

After Pages verification, the durable facts record stores:

```json
{
  "git_pushed": {
    "paths": ["tracking/daily/positions/2026-07-24.md"],
    "deployment": {
      "url": "https://t0nyma.github.io/stock-on/tracking/daily/positions/2026-07-24.html",
      "verified": true
    }
  }
}
```

The existing Git checks still verify that registered paths are committed, clean, and pushed. The durable record is evidence of the external HTTPS verification, not a replacement for Git inspection.

## Data Flow

```text
workflow evidence + decisions + positions
                |
                v
durable workflow facts JSON
                |
                +---- explicit --facts (override)
                |
                v
          existing gate engine
                |
                v
     reproducible preflight/completion result
```

## Error Handling

- Missing record: use empty defaults and retain existing blocking diagnostics.
- Invalid JSON: CLI exits non-zero with the file and parse error.
- Workflow mismatch: CLI exits non-zero.
- Unknown top-level keys: rejected by the facts-record validator.
- Explicit `--facts`: can override individual nested values without deleting unrelated durable evidence.

## Testing

Tests follow red-green order:

1. CLI completion check auto-loads a durable facts record without `--facts`.
2. Explicit facts override durable nested values.
3. Cross-workflow and malformed records fail closed.
4. Position manifests resolve all registered position artifacts.
5. Daily and weekly completion checks pass in a clean Git-backed fixture with valid deployment evidence.
6. Existing gate unit tests and the full repository suite remain green.

## Scope

This change fixes fact persistence and loading only. It does not loosen evidence, decision, freshness, Git, or publication gates; it does not parse report prose; and it does not redesign the report workflows.
