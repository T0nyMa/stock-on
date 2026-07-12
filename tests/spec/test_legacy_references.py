from pathlib import Path


ROOT = Path(__file__).parents[2]
LIVE = [
    ROOT / "AGENTS.md",
    ROOT / "tracking/README.md",
    ROOT / "strategies/README.md",
    ROOT / "src/README.md",
    ROOT / "references/README.md",
] + list((ROOT / "references/scenarios").glob("*.md"))


def test_live_docs_have_no_obsolete_contracts():
    forbidden = (
        ".claude/skills",
        "Claude 分析",
        "全部7只",
        "生成两份日报",
        "data/{code}/regime.json",
    )
    hits = [
        (str(path), phrase)
        for path in LIVE
        for phrase in forbidden
        if phrase in path.read_text(encoding="utf-8")
    ]
    assert hits == []
