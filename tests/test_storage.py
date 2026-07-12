import sqlite3

from src.storage import MarketDataStore


def bars():
    return [
        {
            "date": "2026-07-09",
            "open": 41.0,
            "high": 43.0,
            "low": 40.5,
            "close": 42.5,
            "volume": 1000,
            "amount": 42000,
            "pct_chg": 1.2,
        },
        {
            "date": "2026-07-10T00:00:00",
            "open": 42.5,
            "high": 44.0,
            "low": 42.0,
            "close": 43.2,
            "volume": 1100,
            "amount": 47000,
            "pct_chg": 0.82,
        },
    ]


def test_creates_schema_and_enables_wal(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")

    with sqlite3.connect(store.path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert {"stock_daily", "stock_snapshots", "market_fetch_runs"} <= tables
    assert mode.lower() == "wal"


def test_daily_bar_upsert_is_idempotent_and_accepts_corrections(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")

    assert store.upsert_bars("002050", "三花智控", "SZ", bars()) == 2
    assert store.upsert_bars("002050", "三花智控", "SZ", bars()) == 0
    revised = bars()
    revised[-1]["close"] = 43.25
    store.upsert_bars("002050", "三花智控", "SZ", revised)

    loaded = store.load_bars("002050")
    assert len(loaded) == 2
    assert loaded[-1]["date"] == "2026-07-10"
    assert loaded[-1]["close"] == 43.25
    assert store.latest_bar_date("002050") == "2026-07-10"


def test_load_bars_supports_limit_and_date_bounds(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    store.upsert_bars("002050", "三花智控", "SZ", bars())

    assert [row["date"] for row in store.load_bars("002050", limit=1)] == [
        "2026-07-10"
    ]
    assert [
        row["date"]
        for row in store.load_bars("002050", start="2026-07-10")
    ] == ["2026-07-10"]


def test_snapshot_round_trip_and_missing_value(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    payload = {"price": 43.2, "updated_at": "2026-07-10T15:00:00+08:00"}

    store.save_snapshot("002050", "三花智控", "SZ", "quote", payload)

    assert store.load_snapshot("002050", "quote") == payload
    assert store.load_snapshot("002050", "indicators") is None


def test_fetch_run_is_recorded(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    run_id = store.record_fetch_run(
        code="002050",
        provider="tencent",
        requested_days=500,
        rows_received=500,
        status="success",
    )

    assert run_id > 0
    with sqlite3.connect(store.path) as conn:
        row = conn.execute(
            "SELECT provider, rows_received, status FROM market_fetch_runs WHERE id=?",
            (run_id,),
        ).fetchone()
    assert row == ("tencent", 500, "success")
