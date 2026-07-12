#!/usr/bin/env python3
import argparse,json
from datetime import date

HARD={"latest_official_report","report_version","currency_unit","core_statement_reconciliation"}
SOFT={"critical_notes","segments","latest_call","recent_estimates","recent_regulation","authoritative_media","peers"}

def classify_freshness(event_date,as_of):
    days=(date.fromisoformat(as_of)-date.fromisoformat(event_date)).days
    return "current" if days<=30 else "recent" if days<=90 else "historical"

def validate_payload(p):
    for k in ("schema_version","as_of","company","requirements","sources"):
        if k not in p: raise ValueError(f"missing {k}")
    if p["schema_version"]!=1: raise ValueError("schema_version must be 1")

def evaluate_gate(p):
    validate_payload(p); req={x["id"]:x for x in p["requirements"]}
    missing_h=[x for x in HARD if req.get(x,{}).get("status") not in ("complete","not_applicable")]
    missing_s=[x for x in SOFT if req.get(x,{}).get("status") not in ("complete","not_applicable")]
    total=len(HARD|SOFT); complete=sum(req.get(x,{}).get("status") in ("complete","not_applicable") for x in HARD|SOFT)
    gate="blocked" if missing_h else "partial" if missing_s else "pass"
    allowed={"blocked":"collection_report","partial":"stage_assessment","pass":"full_analysis"}[gate]
    sources=[]
    for s in p["sources"]:
        item=dict(s); item["freshness"]="stale" if item.get("superseded") else classify_freshness(item["event_date"],p["as_of"]); sources.append(item)
    return {**p,"sources":sources,"gaps":sorted(missing_h+missing_s),"coverage_score":round(complete/total*100),"gate_status":gate,"allowed_output":allowed}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output"); a=ap.parse_args(); out=evaluate_gate(json.load(open(a.input)))
    text=json.dumps(out,ensure_ascii=False,indent=2); open(a.output,"w").write(text) if a.output else print(text)
if __name__=="__main__": main()
