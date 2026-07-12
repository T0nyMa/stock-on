from pathlib import Path
import re


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
    assert not re.search(
        r'"buy_ratio": 0\.43.*?"verdict": "偏多".*?"weighted_score": 62',
        strategy,
        re.DOTALL,
    )
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


def test_strategy_skills_return_results_without_sidecars():
    sidecar = re.compile(r"data/\{code\}/strategy_(?!scan\.json)[a-z0-9_]+\.json")
    hits = [
        (str(path), match.group())
        for path in (ROOT / ".agents/skills").glob("*/SKILL.md")
        for match in sidecar.finditer(path.read_text(encoding="utf-8"))
    ]
    for path in (ROOT / ".agents/skills").glob("strategy-*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        if path.name == "SKILL.md" and path.parent.name != "strategy-executor":
            assert "返回给 `$strategy-executor`" in text
    assert hits == []


def test_routed_reporting_and_discovery_skills_have_scalable_contracts():
    weekly = (ROOT / ".agents/skills/weekly-report/SKILL.md").read_text(encoding="utf-8")
    discovery = (ROOT / ".agents/skills/discovery/SKILL.md").read_text(encoding="utf-8")
    executor = (ROOT / ".agents/skills/strategy-executor/SKILL.md").read_text(encoding="utf-8")
    assert "tracking/daily/positions/" in weekly
    split_daily = re.compile(r"tracking/daily/(?:market|[^\s`]+(?:market|positions)/)")
    assert not split_daily.search(weekly)
    assert "YYYY-MM-DD-analysis" not in weekly
    assert not re.search(r"(?:10\s*[-—]\s*15|3\s*[-—]\s*5)\s*只", discovery)
    assert not re.search(r"(?:推荐|候选|进入).*?(?:前\s*)?\d+\s*[-—]\s*\d+\s*只", discovery)
    assert "评分门槛" in discovery and "追踪容量" in discovery
    for ratio in ("buy_ratio", "hold_ratio", "sell_ratio"):
        assert ratio in executor
    assert "weighted_score" in executor
    assert "buy_count" not in executor and "sell_count" not in executor
    assert not re.search(r"\b(?:buy|sell)\s*(?:>=|≥|>|≤|<)\s*\d+", executor)
