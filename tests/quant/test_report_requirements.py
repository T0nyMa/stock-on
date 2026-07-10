from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_daily_workflow_requires_deterministic_quant_context():
    text = read(".agents/skills/daily-report/SKILL.md") + read("AGENTS.md")
    for required in (
        "data/report_context.json", "market_breadth", "multi-timeframe",
        "relative_strength", "ATR", "invalidation", "risk_reward",
        "strategy_stats", "cross_market", "portfolio_risk", "unavailable",
    ):
        assert required in text


def test_weekly_workflow_requires_weekly_indicators_and_prior_call_review():
    text = read(".agents/skills/weekly-report/SKILL.md")
    for required in ("weekly", "breadth", "relative-strength", "prior-call"):
        assert required in text


def test_fetch_pipeline_runs_quant_analysis_and_uses_250_bars():
    text = read("scripts/fetch_all_daily.py")
    assert "limit=250" in text
    assert "run_quant_analysis.py" in text
    fetch = read("src/fetch.py")
    assert 'parser.add_argument("--days", type=int, default=250' in fetch
    assert "days=args.days" in fetch
