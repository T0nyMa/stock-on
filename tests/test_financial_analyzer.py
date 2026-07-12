import importlib.util
from pathlib import Path

P=Path(__file__).parents[1]/'.agents/skills/financial-report-analysis/scripts/analyze_financials.py'
spec=importlib.util.spec_from_file_location('fa',P); fa=importlib.util.module_from_spec(spec); spec.loader.exec_module(fa)

def payload():
    return {'schema_version':1,'company':{'industry_adapter':'manufacturing'},'periods':['2023','2024','2025'],'consolidated':{'revenue':{'2023':100,'2024':110,'2025':120},'receivables':{'2023':10,'2024':14,'2025':19},'inventory':{'2023':10,'2024':10,'2025':10},'operating_cash_flow':{'2023':5,'2024':6,'2025':7},'net_profit':{'2023':10,'2024':10,'2025':10},'cash':{'2025':20},'interest_bearing_debt':{'2025':30}}}

def test_rules_and_missing_are_explicit():
    out=fa.analyze(payload()); rules={x['id']:x['status'] for x in out['rules']}
    assert rules['T001']=='triggered'; assert rules['T005']=='not_triggered'; assert rules['T013']=='triggered'; assert rules['T010']=='triggered'

def test_financial_adapter_disables_industrial_rules():
    p=payload(); p['company']['industry_adapter']='financial'; rules={x['id']:x['status'] for x in fa.analyze(p)['rules']}; assert rules['T001']=='not_applicable'
