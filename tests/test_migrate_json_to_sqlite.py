import json

from scripts.migrate_json_to_sqlite import migrate
from src.data_access import load_bars, load_indicators, load_quote
from src.storage import MarketDataStore


def write_payloads(root):
    stock = root / "data/002050"
    stock.mkdir(parents=True)
    (stock / "kline.json").write_text(json.dumps({
        "code": "002050", "name": "三花智控", "market": "SZ",
        "kline": [
            {"date": "2026-07-09", "close": 42.0, "volume": 100},
            {"date": "2026-07-10", "close": 43.2, "volume": 110},
        ],
        "_evidence": {"source": "fixture"},
    }), encoding="utf-8")
    (stock / "quote.json").write_text(json.dumps({"price": 43.2}), encoding="utf-8")
    (stock / "indicators.json").write_text(json.dumps({"ma": {"ma5": 43.94}}), encoding="utf-8")
    (stock / "broken.json").write_text("not json", encoding="utf-8")
    return stock


def test_migration_is_rerunnable_and_preserves_source_files_by_default(tmp_path):
    stock = write_payloads(tmp_path)
    store = MarketDataStore(tmp_path / "data/stock_analysis.db")

    first = migrate(tmp_path, store=store)
    second = migrate(tmp_path, store=store)

    assert first["files_imported"] == 3
    assert second["files_imported"] == 3
    assert len(load_bars("002050", store=store)["kline"]) == 2
    assert load_quote("002050", store=store)["price"] == 43.2
    assert load_indicators("002050", store=store)["ma"]["ma5"] == 43.94
    assert (stock / "kline.json").exists()


def test_delete_after_verify_removes_only_supported_verified_files(tmp_path):
    stock = write_payloads(tmp_path)
    store = MarketDataStore(tmp_path / "data/stock_analysis.db")

    summary = migrate(tmp_path, store=store, delete_after_verify=True)

    assert summary["files_deleted"] == 3
    assert not (stock / "kline.json").exists()
    assert not (stock / "quote.json").exists()
    assert not (stock / "indicators.json").exists()
    assert (stock / "broken.json").exists()
