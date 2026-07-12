# SQLite Market Data Design

## Goal

Replace per-stock runtime JSON files with one SQLite database that preserves immutable historical market data, supports large initial backfills, and performs idempotent incremental updates afterward.

## Scope

- SQLite is the authoritative store for stock daily bars, latest quotes, fundamentals, news, and computed indicators.
- Existing tracking configuration and human-readable reports remain files.
- Historical bars are upserted by canonical security identity, trade date, and adjustment mode.
- Runtime JSON files under `data/{code}/` are migrated and then removed.
- Market-wide JSON artifacts are outside this migration because they have different schemas and producers.

## Architecture

`src/storage.py` owns schema creation, transactions, upserts, and typed dictionary reads. `src/data_access.py` exposes stable application-level loaders so analysis code does not depend on SQL. Fetchers write directly to SQLite; indicator calculation reads bars and writes the latest indicator snapshot to SQLite. Reports, screeners, and quantitative pipelines use `data_access`.

The database defaults to `data/market.db` and can be overridden with `STOCK_DATA_DB`. SQLite uses WAL mode, foreign keys, busy timeout, and explicit transactions. The database is not committed to Git; reproducible reports remain committed.

## Data Model

- `securities`: canonical identity, display code, name, market, timestamps.
- `daily_bars`: OHLCV, amount, percent change, adjustment mode, source metadata; unique on `(security_id, trade_date, adjustment)`.
- `quotes`: one latest snapshot per security.
- `fundamentals`: one latest snapshot per security.
- `news`: deduplicated by `(security_id, url_hash)` with publication and fetch timestamps.
- `indicators`: one latest JSON payload per security, including evidence metadata.
- `fetch_runs`: audit trail for provider, requested window, rows received, status, and errors.

Flexible snapshot payloads stay as JSON text inside SQLite where their shape changes frequently. Daily bars use normalized columns for range queries, deduplication, and cross-sectional analysis.

## Incremental Update Rules

An initial fetch requests the configured history window, normally 500 trading days. Later fetches query the latest stored date and request an overlap of five trading days. Upsert resolves corrections without duplicating history. A failed or empty provider response never deletes existing rows.

## Migration

The migration command scans `data/{code}/` directories, imports supported JSON files transactionally, reports counts and failures, and only deletes imported runtime JSON after verification. It is safe to rerun. Unrecognized analysis artifacts remain untouched until their consumers migrate.

## Compatibility and Removal

All Python consumers that currently read `kline.json`, `quote.json`, `fundamentals.json`, `news.json`, or `indicators.json` move to `data_access`. Skill and scenario documentation is updated to describe database-backed reads. After repository-wide checks show no runtime references, migrated JSON files are deleted.

## Verification

- Unit tests cover schema creation, idempotent bar upsert, latest-date lookup, snapshot round trips, and incremental-window calculation.
- Migration tests cover reruns and delete-after-verify behavior.
- Indicator tests prove SQLite input/output.
- Existing quantitative and report tests run unchanged or with database fixtures.
- A live 002050 fetch proves an initial 500-row load followed by an idempotent incremental refresh.

