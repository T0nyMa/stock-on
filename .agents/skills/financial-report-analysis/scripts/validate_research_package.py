#!/usr/bin/env python3
import csv
import json
import re
import sys
from pathlib import Path


SOURCE_FOLDERS = ("official", "earnings-calls", "estimates", "media", "regulatory", "peers")
TABLE_COLUMNS = {
    "group-quarterly.csv": {"period", "revenue", "operating_income", "net_income", "operating_cash_flow", "capex", "free_cash_flow", "source_ids"},
    "segments.csv": {"period", "segment", "revenue", "yoy", "adjusted_ebita", "margin", "source_ids"},
    "estimates.csv": {"institution", "date", "period", "metric", "old_estimate", "new_estimate", "basis", "validation_event", "source_ids"},
    "peers.csv": {"company", "period", "metric", "value", "comparability", "source_ids"},
}
REPORT_SECTIONS = (
    "研究范围与信息完整性", "最近一年季度趋势和重大事件时间线", "集团三表分析", "业务分部分析",
    "资本开支与资本配置", "电话会解读", "机构预测", "同行横向比较", "会计、治理和监管风险",
    "综合问题、机会、反方与后续验证", "来源、计算公式和限制",
)
ANALYSIS_CHAIN = ("事实数据", "变化计算", "管理层解释", "外部预测", "分析判断", "最强反方", "下一期验证指标")
EVIDENCE_ID = re.compile(r"E-\d{3,}")


def validate(research: Path, report: Path):
    errors = []
    if not research.is_dir():
        return [f"missing research directory: {research}"]
    for folder in SOURCE_FOLDERS:
        path = research / folder
        if not path.is_dir() or not any(p.is_file() for p in path.iterdir()):
            errors.append(f"missing or empty source folder: {folder}")

    index = research / "index.md"
    index_text = index.read_text(encoding="utf-8") if index.is_file() else ""
    if not index_text:
        errors.append("missing source index: index.md")
    if "Extracted fact" not in index_text and "提取事实" not in index_text:
        errors.append("source index requires an Extracted fact/提取事实 column; links alone are insufficient")
    indexed_ids = set(EVIDENCE_ID.findall(index_text))
    if not indexed_ids:
        errors.append("source index has no evidence IDs")

    for name, expected in TABLE_COLUMNS.items():
        path = research / "tables" / name
        if not path.is_file():
            errors.append(f"missing table: tables/{name}")
            continue
        with path.open(encoding="utf-8-sig", newline="") as handle:
            columns = set(next(csv.reader(handle), []))
        missing = expected - columns
        if missing:
            errors.append(f"table {name} missing columns: {', '.join(sorted(missing))}")

    claims = research / "claims.json"
    if not claims.is_file():
        errors.append("missing claims.json")
    else:
        try:
            payload = json.loads(claims.read_text(encoding="utf-8"))
            for claim in payload.get("claims", []):
                for evidence_id in claim.get("evidence_ids", []):
                    if evidence_id not in indexed_ids:
                        errors.append(f"claim {claim.get('id', 'unknown')} references unindexed evidence {evidence_id}")
        except (json.JSONDecodeError, AttributeError) as exc:
            errors.append(f"invalid claims.json: {exc}")

    report_text = report.read_text(encoding="utf-8") if report.is_file() else ""
    if not report_text:
        errors.append(f"missing report: {report}")
    for section in REPORT_SECTIONS:
        if section not in report_text:
            errors.append(f"missing report section: {section}")
    missing_chain = [label for label in ANALYSIS_CHAIN if label not in report_text]
    if missing_chain:
        errors.append(f"report analysis chain missing: {', '.join(missing_chain)}")
    report_ids = set(EVIDENCE_ID.findall(report_text))
    if report_text and not report_ids:
        errors.append("report has no evidence references")
    for evidence_id in report_ids:
        if evidence_id not in indexed_ids:
            errors.append(f"report references unindexed evidence {evidence_id}")
    return errors


def main():
    if len(sys.argv) != 3:
        print("usage: validate_research_package.py RESEARCH_DIR REPORT.md")
        return 2
    errors = validate(Path(sys.argv[1]), Path(sys.argv[2]))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("research package valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
