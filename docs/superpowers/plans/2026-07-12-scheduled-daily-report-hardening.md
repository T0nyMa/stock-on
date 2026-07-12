# Scheduled Daily Report Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make weekday 17:00 daily-report automation enforce the refactored single-file, spec-gated, published-report contract.

**Architecture:** Keep launchd and its lock wrapper. Add a deterministic Python post-run verifier, update the Codex prompt, and turn the legacy multi-file orchestrator into a failing compatibility stub.

**Tech Stack:** zsh, Python 3.12, pytest, Git, launchd.

## Global Constraints

- The only Markdown report artifact is `tracking/daily/positions/YYYY-MM-DD.md`.
- Search uses AnySearch first and EasyAnySearch only as fallback.
- A run succeeds only after commit, push, HTML generation, index update, and published-page verification.
- Existing weekday 17:00 Asia/Shanghai LaunchAgent schedule remains unchanged.

---

### Task 1: Contract tests

**Files:**
- Create: `tests/automation/test_scheduled_daily.py`

**Interfaces:**
- Consumes: repository wrapper and verifier CLI.
- Produces: regression tests for prompt, single-file output, Git state, and legacy entrypoint.

- [ ] Write tests that assert the wrapper names AnySearch priority, spec checks, verifier invocation, and no legacy generation.
- [ ] Write verifier tests using a temporary Git remote and seven-section report.
- [ ] Run `pytest tests/automation/test_scheduled_daily.py -v` and confirm failure before implementation.

### Task 2: Deterministic post-run verifier

**Files:**
- Create: `scripts/verify_scheduled_daily.py`

**Interfaces:**
- Consumes: `--date YYYY-MM-DD`, repository state, optional `--skip-http` for tests.
- Produces: exit 0 with JSON success or exit 1 with explicit invariant failures.

- [ ] Validate the canonical Markdown and seven headings.
- [ ] Reject dated legacy market and per-stock Markdown artifacts.
- [ ] Validate HTML/index, clean applicable paths, pushed commit, and publication URL.
- [ ] Run focused tests to green.

### Task 3: Wrapper and legacy isolation

**Files:**
- Modify: `scripts/run_scheduled_daily.sh`
- Modify: `scripts/orchestrate_daily.py`

**Interfaces:**
- Consumes: Codex CLI and verifier.
- Produces: non-zero launchd status for incomplete work.

- [ ] Update the prompt to use AnySearch-first, current workflow/spec, single-file generation, and current research snapshots.
- [ ] Invoke the verifier after Codex exits.
- [ ] Replace legacy orchestrator execution with a clear non-zero migration message.
- [ ] Run automation, spec, and report-contract tests.
- [ ] Reload the unchanged LaunchAgent plist and inspect its live schedule.
