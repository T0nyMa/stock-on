# Scheduled Daily Report Hardening Design

## Goal

Keep the existing weekday 17:00 LaunchAgent, but make a scheduled run obey the current single-file daily-report contract and fail deterministically when generation, Git push, deployment, or publication verification is incomplete.

## Design

`scripts/run_scheduled_daily.sh` remains the only launchd entrypoint. It invokes Codex with the current AnySearch-first, spec-driven prompt, then invokes a new read-only verifier. The verifier checks the seven-section Markdown, rejects legacy per-stock and market Markdown created for the same date, verifies HTML/index artifacts, confirms the report and applicable position files are committed and pushed, and optionally checks the published URL. Any failed invariant returns non-zero.

`scripts/orchestrate_daily.py` is retained only as a compatibility tombstone: execution exits with a clear message directing callers to the scheduled Codex workflow, preventing the legacy multi-file generator from being used accidentally.

The LaunchAgent schedule, working directory, lock, timezone, and approval bypass remain unchanged. Tests inspect the real wrapper and execute the verifier against temporary Git repositories.

## Error handling

The shell uses `set -eu`; Codex failure or verifier failure makes launchd record a non-zero exit. The last assistant message remains diagnostic context, not proof of completion. Publication verification may be skipped only through an explicit verifier flag for local tests, never by the production wrapper.
