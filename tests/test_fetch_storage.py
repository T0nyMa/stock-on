from datetime import date
from functools import partial
from types import SimpleNamespace

import src.fetch as fetch_module
from src.data_access import load_bars, load_quote
from src.storage import MarketDataStore


class FakeEvidence:
    source = "fixture"
    source_chain = ["fixture:ok"]

    def to_dict(self):
        return {"source": self.source, "source_chain": self.source_chain, "gaps": []}


class FakeKlineProvider:
    limits = []

    def get_daily(self, code, limit):
        self.limits.append(limit)
        rows = [
            SimpleNamespace(date="2026-07-09", open=41, high=43, low=40, close=42, volume=100, amount=4200, pct_chg=1),
            SimpleNamespace(date="2026-07-10", open=42, high=44, low=41, close=43.2, volume=110, amount=4700, pct_chg=0.82),
        ]
        return rows, FakeEvidence()


class FakeQuoteProvider:
    def get_realtime(self, code):
        return SimpleNamespace(
            name="三花智控", price=43.2, change_pct=0.82, volume=110,
            amount=4700, turnover_rate=3.04, pe=44.48, pb=5.57,
            market_cap=1600, source="fixture", source_chain=["fixture:ok"],
        )


def test_v2_fetch_initializes_then_uses_incremental_window(tmp_path, monkeypatch):
    store = MarketDataStore(tmp_path / "market.db")
    FakeKlineProvider.limits = []
    monkeypatch.setattr(fetch_module, "KlineProvider", FakeKlineProvider)
    monkeypatch.setattr(fetch_module, "QuoteProvider", FakeQuoteProvider)
    monkeypatch.setattr(fetch_module, "setup_env", lambda: None)
    monkeypatch.setattr(
        fetch_module,
        "incremental_days",
        partial(fetch_module.incremental_days, as_of=date(2026, 7, 12)),
    )

    fetch_module.fetch_stock_data(
        "002050", provider="v2", days=500, store=store, include_context=False
    )
    fetch_module.fetch_stock_data(
        "002050", provider="v2", days=500, store=store, include_context=False
    )

    assert FakeKlineProvider.limits == [500, 5]
    assert len(load_bars("002050", store=store)["kline"]) == 2
    assert load_quote("002050", store=store)["price"] == 43.2
