import importlib.util
import json
from pathlib import Path

import pytest

from src.storage import MarketDataStore


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents/skills/deep-stock-analysis"
ADAPTERS = (
    "resource-cycle",
    "technology-growth",
    "manufacturing",
    "consumer",
    "healthcare",
    "financial",
    "internet-platform",
)


def _snapshot_module():
    path = SKILL / "scripts/research_snapshot.py"
    spec = importlib.util.spec_from_file_location("research_snapshot", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_skill_package_contract():
    required = [
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/research_snapshot.py",
        "references/core-framework.md",
        "references/integration-contract.md",
        "references/report-template.md",
        "references/analysis-gaps.md",
        *[f"references/{name}.md" for name in ADAPTERS],
    ]
    assert all((SKILL / path).is_file() for path in required)

    text = (SKILL / "SKILL.md").read_text()
    for phrase in (
        "Phase 0",
        "Phase 10",
        "research_evidence",
        "research_summary",
        "主要适配器",
        "次要适配器",
        "不得输出",
        "来源链接",
        "quality",
    ):
        assert phrase in text


def test_four_forward_cases_route_to_distinct_adapters():
    text = (SKILL / "SKILL.md").read_text()
    expected = {
        "紫金": "资源周期",
        "三花": "制造业+科技成长",
        "恒瑞": "医药",
        "阿里": "互联网平台",
    }
    for company, route in expected.items():
        assert f"{company}→{route}" in text

    contents = {
        name: (SKILL / f"references/{name}.md").read_text()
        for name in ("resource-cycle", "manufacturing", "technology-growth", "healthcare", "internet-platform")
    }
    assert "单位现金成本" in contents["resource-cycle"]
    assert "产能利用率" in contents["manufacturing"]
    assert "客户验证" in contents["technology-growth"]
    assert "临床入组" in contents["healthcare"]
    assert "网络效应" in contents["internet-platform"]


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_adapter_contract(adapter):
    text = (SKILL / f"references/{adapter}.md").read_text()
    for heading in ("价值驱动", "领先指标", "估值", "风险", "证伪"):
        assert heading in text


def test_strategy_executor_has_backward_compatible_research_mode():
    executor = (ROOT / ".agents/skills/strategy-executor/SKILL.md").read_text()
    regime = (ROOT / ".agents/skills/market-regime/SKILL.md").read_text()
    assert "mode=trading|research" in executor
    assert '"signal": "buy"' in executor
    assert all(word in executor for word in ("uncertainty", "invalidation", "不得包含操作建议"))
    assert "research mode" in regime


def test_snapshot_validation_and_round_trip(tmp_path):
    module = _snapshot_module()
    store = MarketDataStore(tmp_path / "market.db")
    evidence = {
        "schema_version": 1,
        "as_of": "2026-07-12",
        "items": [{
            "claim": "收入依赖铜金价格",
            "value": "铜金业务为核心利润来源",
            "period": "2025FY",
            "source_type": "annual_report",
            "source": "公司年报",
            "published_at": "2026-03-20",
            "url": "https://example.com/report",
            "quality": "primary",
            "status": "verified",
        }],
    }
    summary = {
        "schema_version": 1,
        "as_of": "2026-07-12",
        "company_type": {"primary": "resource-cycle", "secondary": None},
        "thesis": ["低成本资源运营能力是核心优势"],
        "falsification": ["单位成本持续恶化"],
        "confidence": "medium",
        "source_report": "tracking/601899-紫金矿业/deep-analysis-2026-07-12.md",
    }

    module.save_payload(store, "601899", "紫金矿业", "SH", "research_evidence", evidence)
    module.save_payload(store, "HK09988", "阿里巴巴", "HK", "research_summary", summary)
    assert store.load_snapshot("601899", "research_evidence") == evidence
    assert store.load_snapshot("09988", "research_summary") == summary


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("quote", {}),
        ("research_evidence", {"schema_version": 1, "as_of": "2026-07-12", "items": []}),
        ("research_evidence", {"schema_version": 1, "as_of": "2026-07-12", "items": [{"claim": "x", "source": "x", "published_at": "2026-01-01", "quality": "bad", "status": "verified"}]}),
        ("research_summary", {"schema_version": 1, "as_of": "2026-07-12"}),
    ],
)
def test_snapshot_rejects_invalid_payload(kind, payload, tmp_path):
    module = _snapshot_module()
    store = MarketDataStore(tmp_path / "market.db")
    with pytest.raises(ValueError):
        module.save_payload(store, "002050", "三花智控", "SZ", kind, payload)
