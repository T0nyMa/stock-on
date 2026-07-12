import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
VALIDATOR = ROOT / ".agents/skills/financial-report-analysis/scripts/validate_research_package.py"


def run_validator(research: Path, report: Path):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(research), str(report)],
        capture_output=True,
        text=True,
    )


def make_complete_package(tmp_path: Path):
    research = tmp_path / "research"
    for folder in ("official", "earnings-calls", "estimates", "media", "regulatory", "peers", "tables"):
        (research / folder).mkdir(parents=True, exist_ok=True)
        if folder != "tables":
            (research / folder / "source.md").write_text("# Source\n\nEvidence: E-001\n", encoding="utf-8")
    (research / "index.md").write_text(
        "# Index\n\n| ID | Date | Source | URL | Extracted fact |\n|---|---|---|---|---|\n"
        "| E-001 | 2026-07-01 | Official | https://example.com | Revenue was 100 |\n",
        encoding="utf-8",
    )
    required_tables = {
        "group-quarterly.csv": "period,revenue,operating_income,net_income,operating_cash_flow,capex,free_cash_flow,source_ids\n",
        "segments.csv": "period,segment,revenue,yoy,adjusted_ebita,margin,source_ids\n",
        "estimates.csv": "institution,date,period,metric,old_estimate,new_estimate,basis,validation_event,source_ids\n",
        "peers.csv": "company,period,metric,value,comparability,source_ids\n",
    }
    for name, header in required_tables.items():
        (research / "tables" / name).write_text(header + "sample,1,E-001\n", encoding="utf-8")
    (research / "claims.json").write_text(
        json.dumps({"claims": [{"id": "C-001", "text": "A claim", "evidence_ids": ["E-001"]}]}),
        encoding="utf-8",
    )
    report = tmp_path / "report.md"
    sections = (
        "研究范围与信息完整性", "最近一年季度趋势和重大事件时间线", "集团三表分析", "业务分部分析",
        "资本开支与资本配置", "电话会解读", "机构预测", "同行横向比较", "会计、治理和监管风险",
        "综合问题、机会、反方与后续验证", "来源、计算公式和限制",
    )
    report.write_text(
        "# Report\n\n" + "\n".join(f"## {section}\n\n事实数据；变化计算；管理层解释；外部预测；分析判断；最强反方；下一期验证指标。[E-001]" for section in sections),
        encoding="utf-8",
    )
    return research, report


def test_validator_accepts_complete_research_package(tmp_path):
    research, report = make_complete_package(tmp_path)
    result = run_validator(research, report)
    assert result.returncode == 0, result.stdout + result.stderr


def test_validator_rejects_link_only_index(tmp_path):
    research, report = make_complete_package(tmp_path)
    (research / "index.md").write_text("# Index\n\nhttps://example.com\n", encoding="utf-8")
    result = run_validator(research, report)
    assert result.returncode == 1
    assert "extracted fact" in result.stdout.lower()


def test_validator_rejects_report_without_analysis_chain(tmp_path):
    research, report = make_complete_package(tmp_path)
    report.write_text("# Report\n\n## 研究范围与信息完整性\n\n[E-001]", encoding="utf-8")
    result = run_validator(research, report)
    assert result.returncode == 1
    assert "missing report section" in result.stdout.lower()
    assert "analysis chain" in result.stdout.lower()
