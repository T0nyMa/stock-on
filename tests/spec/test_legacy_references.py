from pathlib import Path


ROOT = Path(__file__).parents[2]
LIVE = [
    ROOT / "AGENTS.md",
    ROOT / "tracking/README.md",
    ROOT / "strategies/README.md",
    ROOT / "src/README.md",
    ROOT / "references/README.md",
] + list((ROOT / "references/scenarios").glob("*.md")) + list(
    (ROOT / ".agents/skills").glob("*/SKILL.md")
)


def test_live_docs_have_no_obsolete_contracts():
    forbidden = (
        ".claude/skills",
        "Claude 分析",
        "全部7只",
        "生成两份日报",
        "data/{code}/regime.json",
        "strategy_*.json",
        "tracking/daily/market/YYYY-MM-DD.md",
        "tracking/{code}-{name}/YYYY-MM-DD-analysis.md",
        "core: 3-5",
        "key: 2-3",
        "watch: 1-2",
    )
    hits = [
        (str(path), phrase)
        for path in LIVE
        for phrase in forbidden
        if phrase in path.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_daily_skill_uses_one_registered_markdown_report_and_deploy_html():
    text = (ROOT / ".agents/skills/daily-report/SKILL.md").read_text(encoding="utf-8")
    assert "artifact.daily_report" in text
    assert "tracking/daily/positions/YYYY-MM-DD.md" in text
    assert "HTML" in text and "$deploy" in text
    assert "七章" in text


def test_strategy_consensus_and_discovery_scale_with_candidate_count():
    strategy = (ROOT / "references/scenarios/strategy-scan.md").read_text(encoding="utf-8")
    discovery = (ROOT / "references/scenarios/discovery.md").read_text(encoding="utf-8")
    assert "buy_ratio" in strategy and "sell_ratio" in strategy
    assert "buy ≥ 5" not in strategy and "sell ≥ 4" not in strategy
    assert "推荐 2-4 只" not in discovery
    assert "容量" in discovery and "门槛" in discovery


def test_tracking_tiers_have_stable_semantics():
    text = (ROOT / "tracking/README.md").read_text(encoding="utf-8")
    for tier in ("core", "key", "watch"):
        assert f"`{tier}`" in text


def test_regime_and_decision_skills_only_consume_registered_inputs():
    regime = (ROOT / ".agents/skills/market-regime/SKILL.md").read_text(encoding="utf-8")
    decision = (ROOT / ".agents/skills/decision-agent/SKILL.md").read_text(encoding="utf-8")
    assert "snapshot.indicators" in regime
    assert "不写入旁路文件" in regime
    for artifact in (
        "artifact.strategy_scan",
        "artifact.report_context",
        "artifact.research_summary",
        "artifact.financial_quality_summary",
        "artifact.discovery_report",
    ):
        assert artifact in decision
    assert "decision.json" not in decision
