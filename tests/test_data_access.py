from datetime import date

from src.data_access import (
    incremental_days,
    load_bars,
    load_fundamentals,
    load_indicators,
    load_quote,
    load_research_evidence,
    load_research_summary,
    query_payload,
)
from src.storage import MarketDataStore


def test_loaders_preserve_application_payload_shapes(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    store.upsert_bars(
        "002050",
        "三花智控",
        "SZ",
        [{"date": "2026-07-10", "open": 42, "high": 44, "low": 41, "close": 43.2, "volume": 100}],
        source="tencent",
    )
    store.save_snapshot("002050", "三花智控", "SZ", "quote", {"price": 43.2})
    store.save_snapshot("002050", "三花智控", "SZ", "fundamentals", {"pe": 44.48})
    store.save_snapshot("002050", "三花智控", "SZ", "indicators", {"ma": {"ma5": 43.94}})

    payload = load_bars("002050", store=store)
    assert payload["code"] == "002050"
    assert payload["kline"][0]["close"] == 43.2
    assert payload["_evidence"]["source"] == "tencent"
    assert load_quote("002050", store=store) == {"price": 43.2}
    assert load_fundamentals("002050", store=store) == {"pe": 44.48}
    assert load_indicators("002050", store=store) == {"ma": {"ma5": 43.94}}


def test_research_snapshot_loaders_are_available_to_report_workflows(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    summary = {"schema_version": 1, "thesis": ["test"]}
    evidence = {"schema_version": 1, "items": [{"claim": "test"}]}
    store.save_snapshot("002050", "三花智控", "SZ", "research_summary", summary)
    store.save_snapshot("002050", "三花智控", "SZ", "research_evidence", evidence)

    assert load_research_summary("002050", store=store) == summary
    assert load_research_evidence("002050", store=store) == evidence
    assert query_payload("002050", "research_summary", store=store) == summary
    assert query_payload("002050", "research_evidence", store=store) == evidence


def test_incremental_days_uses_full_backfill_for_empty_store(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")

    assert incremental_days("002050", store=store, full_days=500, as_of=date(2026, 7, 12)) == 500


def test_incremental_days_overlaps_recent_history_and_catches_up_gaps(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    store.upsert_bars(
        "002050",
        "三花智控",
        "SZ",
        [{"date": "2026-07-10", "close": 43.2}],
    )
    assert incremental_days("002050", store=store, overlap=5, as_of=date(2026, 7, 12)) == 5

    old_store = MarketDataStore(tmp_path / "old.db")
    old_store.upsert_bars(
        "002050",
        "三花智控",
        "SZ",
        [{"date": "2026-06-26", "close": 43.2}],
    )
    assert incremental_days("002050", store=old_store, overlap=5, as_of=date(2026, 7, 12)) == 15


def test_bare_hong_kong_code_resolves_to_canonical_storage_code(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    store.upsert_bars(
        "HK09988", "阿里巴巴", "HK",
        [{"date": "2026-07-10", "close": 110.2}],
    )
    store.save_snapshot("HK09988", "阿里巴巴", "HK", "quote", {"price": 110.2})

    assert load_bars("09988", store=store)["kline"][0]["close"] == 110.2
    assert load_quote("09988", store=store) == {"price": 110.2}
