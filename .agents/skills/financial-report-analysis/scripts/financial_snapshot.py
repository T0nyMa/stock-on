#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
KINDS={"financial_report_evidence","financial_quality_summary","financial_collection_status"}
def validate(kind,p):
    if kind not in KINDS: raise ValueError("unsupported kind")
    for k in ("schema_version","as_of"):
        if not p.get(k): raise ValueError(f"missing {k}")
    if kind=="financial_report_evidence" and not isinstance(p.get("items"),list): raise ValueError("items required")
    if kind=="financial_quality_summary":
        for k in ("score","rating","judgment","issues","source_report"):
            if k not in p: raise ValueError(f"missing {k}")
        if p["rating"] not in "ABCDE": raise ValueError("invalid rating")
    if kind=="financial_collection_status":
        for k in ("requirements","sources","gaps","coverage_score","gate_status","allowed_output"):
            if k not in p: raise ValueError(f"missing {k}")
        if p["gate_status"] not in ("pass","partial","blocked"): raise ValueError("invalid gate_status")
def save_payload(store,code,name,market,kind,p): validate(kind,p); store.save_snapshot(code,name,market,kind,p)
def main():
    ap=argparse.ArgumentParser(); [ap.add_argument(x,required=True) for x in ("--code","--name","--market","--kind","--input")]; ap.add_argument("--db",default="data/stock_analysis.db"); a=ap.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[4])); from src.storage import MarketDataStore
    save_payload(MarketDataStore(a.db),a.code,a.name,a.market,a.kind,json.load(open(a.input)))
if __name__=="__main__": main()
