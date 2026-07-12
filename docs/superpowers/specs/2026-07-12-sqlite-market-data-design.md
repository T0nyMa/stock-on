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

The existing SQLAlchemy-backed `src/storage.py` owns schema creation, transactions, upserts, and typed dictionary reads. `src/data_access.py` exposes stable application-level loaders so analysis code does not depend on SQL. Fetchers write directly to SQLite; indicator calculation reads bars and writes the latest indicator snapshot to SQLite. Reports, screeners, and quantitative pipelines use `data_access`.

The database remains the project's existing `data/stock_analysis.db` and can be overridden with `DATABASE_PATH`. SQLite uses WAL mode, busy timeout, write-lock retries, and explicit transactions. The database is not committed to Git; reproducible reports remain committed.

## Data Model

- `stock_daily`: normalized OHLCV, amount, percent change, calculated moving averages, and source metadata; unique on `(code, date)`.
- `stock_snapshots`: one latest JSON payload per `(code, kind)` for quote, fundamentals, news, and indicators.
- `market_fetch_runs`: audit trail for provider, requested window, rows received, status, and errors.

Flexible snapshot payloads stay as JSON text inside SQLite where their shape changes frequently. Daily bars use normalized columns for range queries, deduplication, and cross-sectional analysis. Existing analysis-history and operational tables remain in the same database.

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
