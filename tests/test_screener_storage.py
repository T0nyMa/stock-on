from src.screener import score_l2
from src.storage import MarketDataStore


def test_screener_returns_no_score_when_sqlite_data_is_missing(tmp_path):
    store = MarketDataStore(tmp_path / "market.db")

    assert score_l2("002050", store=store) == (None, None)
