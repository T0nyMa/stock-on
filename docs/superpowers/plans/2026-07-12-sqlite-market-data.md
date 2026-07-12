# SQLite Market Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SQLite the sole runtime store for per-stock history and snapshots, with initial backfill and idempotent incremental updates.

**Architecture:** A focused storage module owns SQLite, while a data-access facade isolates application consumers from SQL. Fetching and indicator computation write to the database; reports and analysis read through the facade. A verified migration removes legacy runtime JSON.

**Tech Stack:** Python 3, stdlib `sqlite3`, pandas, pytest

## Global Constraints

- Default database path is `data/market.db`; `STOCK_DATA_DB` overrides it.
- Historical bar uniqueness is `(security_id, trade_date, adjustment)`.
- Initial history defaults to 500 trading days; incremental refresh overlaps five trading days.
- Existing data is never deleted on an empty or failed provider response.
- Tracking configuration, market-wide artifacts, and human-readable reports remain files.

---

### Task 1: SQLite repository

**Files:**
- Create: `src/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Produces: `MarketDataStore`, `get_store`, canonical security upserts, bar and snapshot reads/writes.

- [ ] Write failing tests for schema creation, idempotent daily-bar upsert, date-bounded reads, and snapshot round trips.
- [ ] Run `pytest tests/test_storage.py -q` and confirm failures are caused by the missing module.
- [ ] Implement the minimal repository with WAL, foreign keys, busy timeout, transactions, unique constraints, and JSON payload encoding.
- [ ] Run `pytest tests/test_storage.py -q` and confirm all tests pass.

### Task 2: Data access facade and incremental policy

**Files:**
- Create: `src/data_access.py`
- Test: `tests/test_data_access.py`

**Interfaces:**
- Consumes: `MarketDataStore`.
- Produces: `load_bars`, `load_quote`, `load_fundamentals`, `load_news`, `load_indicators`, `incremental_days`.

- [ ] Write failing tests proving application payload compatibility and that an empty database requests the full backfill while an existing history requests a five-session overlap.
- [ ] Run `pytest tests/test_data_access.py -q` and confirm expected failures.
- [ ] Implement the facade and incremental-window calculation.
- [ ] Run `pytest tests/test_data_access.py -q` and confirm all tests pass.

### Task 3: Fetch and indicator database integration

**Files:**
- Modify: `src/fetch.py`
- Modify: `src/indicators.py`
- Modify: `tests/test_indicators.py`
- Test: `tests/test_fetch_storage.py`

**Interfaces:**
- Fetch writes bars and snapshots using `MarketDataStore` and records fetch runs.
- Indicators consume `load_bars` and write the latest indicator payload.

- [ ] Write failing tests for database writes, repeat-fetch idempotence, and indicator database output.
- [ ] Run the focused tests and confirm they fail for missing integration.
- [ ] Replace runtime JSON writes and reads with repository calls; preserve CLI arguments and provider behavior.
- [ ] Run focused tests and confirm they pass.

### Task 4: Consumer migration

**Files:**
- Modify: `src/report_lib.py`
- Modify: `src/screener.py`
- Modify: `src/quant/pipeline.py`
- Modify: `scripts/orchestrate_daily.py`
- Modify: `scripts/generate_daily_v2.py`
- Modify: `scripts/gen_positions_summary.py`
- Modify: `scripts/gen_daily_reports.py`
- Modify: relevant tests under `tests/`

**Interfaces:**
- All per-stock runtime reads use `src.data_access`; report output contracts remain unchanged.

- [ ] Add or update fixtures so each consumer is exercised against a temporary SQLite database.
- [ ] Run focused tests and confirm failures identify remaining JSON assumptions.
- [ ] Migrate each consumer to the facade without changing report semantics.
- [ ] Run focused tests and confirm they pass.

### Task 5: Verified migration and JSON removal

**Files:**
- Create: `scripts/migrate_json_to_sqlite.py`
- Test: `tests/test_migrate_json_to_sqlite.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces a rerunnable migration CLI with `--delete-after-verify` and a machine-readable summary.

- [ ] Write failing tests for import counts, rerun idempotence, verification, and selective deletion.
- [ ] Run `pytest tests/test_migrate_json_to_sqlite.py -q` and confirm expected failures.
- [ ] Implement migration, verification, and selective removal.
- [ ] Run migration tests and confirm they pass.
- [ ] Run the migration on the workspace and remove only the five migrated per-stock runtime JSON names.

### Task 6: Documentation and end-to-end verification

**Files:**
- Modify: `src/README.md`
- Modify: `AGENTS.md`
- Modify: `references/scenarios/*.md` where runtime JSON is named.
- Modify: relevant `.agents/skills/*/SKILL.md` files where runtime JSON is named.

**Interfaces:**
- Documentation directs agents and users to commands and data-access functions rather than deleted files.

- [ ] Replace per-stock runtime JSON instructions with SQLite-backed access instructions.
- [ ] Run `rg` to ensure no executable Python consumer references the five removed JSON filenames.
- [ ] Run the complete pytest suite.
- [ ] Fetch 002050 with 500 initial days, rerun incrementally, recompute indicators, and verify row count and uniqueness in SQLite.
- [ ] Run the daily report data preparation smoke check without publishing.

