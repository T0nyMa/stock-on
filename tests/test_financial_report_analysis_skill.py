from pathlib import Path
ROOT=Path(__file__).parents[1]; SK=ROOT/'.agents/skills/financial-report-analysis'
def test_package_contract():
    assert (SK/'SKILL.md').is_file(); text=(SK/'SKILL.md').read_text()
    for x in ('最近五年','Phase 0','Phase 10','合并报表','母公司报表','financial_quality_summary','不得输出'):
        assert x in text
    for f in ('evidence-schema','normalization-contract','accounting-comparability','deterministic-rules','scoring-system','issue-card-playbook','risk-control','market-adapters','industry-adapters','report-template','analysis-gaps'):
        assert (SK/f'references/{f}.md').is_file()
def test_integration_routes():
    assert '$financial-report-analysis' in (ROOT/'AGENTS.md').read_text()
    assert 'financial_quality_summary' in (ROOT/'.agents/skills/deep-stock-analysis/SKILL.md').read_text()
