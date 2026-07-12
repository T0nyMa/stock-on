import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/'.agents/skills/financial-report-analysis/scripts/collection_status.py'
s=importlib.util.spec_from_file_location('cs',P); cs=importlib.util.module_from_spec(s); s.loader.exec_module(cs)
ALL=cs.HARD|cs.SOFT
def payload(missing=()):
 return {'schema_version':1,'as_of':'2026-07-12','company':{'code':'09988'},'requirements':[{'id':x,'status':'missing' if x in missing else 'complete'} for x in ALL],'sources':[{'event_date':'2026-06-12','published_at':'2026-06-13','quality':'primary'},{'event_date':'2026-04-13','published_at':'2026-04-13','quality':'secondary'},{'event_date':'2026-07-10','published_at':'2026-07-10','quality':'weak','superseded':True}]}
def test_freshness_boundaries():
 assert cs.classify_freshness('2026-06-12','2026-07-12')=='current'; assert cs.classify_freshness('2026-04-13','2026-07-12')=='recent'; assert cs.classify_freshness('2026-04-12','2026-07-12')=='historical'
def test_gate_outputs():
 assert cs.evaluate_gate(payload())['gate_status']=='pass'; assert cs.evaluate_gate(payload({'latest_call'}))['allowed_output']=='stage_assessment'; assert cs.evaluate_gate(payload({'latest_official_report'}))['allowed_output']=='collection_report'; assert cs.evaluate_gate(payload())['sources'][-1]['freshness']=='stale'
