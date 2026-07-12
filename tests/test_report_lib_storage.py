from src.report_lib import load_stock_data
from src.storage import MarketDataStore


def test_report_loader_reads_stock_snapshots_from_sqlite(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")
    store.save_snapshot("002050", "三花智控", "SZ", "indicators", {"trend": {"status": "震荡"}})
    store.save_snapshot("002050", "三花智控", "SZ", "quote", {"price": 43.2})
    store.save_snapshot("002050", "三花智控", "SZ", "fundamentals", {"pe": 44.48})

    indicators, quote, fundamentals = load_stock_data("002050", store=store)

    assert indicators["trend"]["status"] == "震荡"
    assert quote["price"] == 43.2
    assert fundamentals["pe"] == 44.48
