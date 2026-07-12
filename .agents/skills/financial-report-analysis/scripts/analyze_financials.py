#!/usr/bin/env python3
import argparse, json

def ratio(a,b): return None if a is None or b in (None,0) else a/b
def growth(a,b): return None if a is None or b in (None,0) else a/b-1
def validate_payload(p):
    for k in ("schema_version","company","periods","consolidated"):
        if k not in p: raise ValueError(f"missing {k}")
    if p["schema_version"] != 1: raise ValueError("schema_version must be 1")

def analyze(p):
    validate_payload(p); periods=p["periods"]; c=p["consolidated"]; rules=[]; gaps=[]
    def series(name):
        v=c.get(name,{}); return [v.get(x) for x in periods]
    revenue, rec, inv, ocf, profit = map(series,("revenue","receivables","inventory","operating_cash_flow","net_profit"))
    def trend_rule(code,a,b,margin):
        available=all(x is not None for x in a[-3:]+b[-3:]) and len(periods)>=3
        hit=available and all(growth(a[i],a[i-1])-growth(b[i],b[i-1])>margin for i in (-2,-1))
        rules.append({"id":code,"status":"triggered" if hit else "not_triggered" if available else "unavailable"})
    if p.get("company",{}).get("industry_adapter")=="financial":
        rules.extend({"id":x,"status":"not_applicable"} for x in ("T001","T005","T013"))
    else:
        trend_rule("T001",rec,revenue,.10); trend_rule("T005",inv,revenue,.15)
        vals=[ratio(ocf[i],profit[i]) for i in range(len(periods))]
        rules.append({"id":"T013","status":"triggered" if len(vals)>=3 and all(x is not None and x<1 for x in vals[-3:]) else "not_triggered" if len(vals)>=3 and all(x is not None for x in vals[-3:]) else "unavailable"})
    cash=series("cash"); debt=series("interest_bearing_debt")
    cr=ratio(cash[-1],debt[-1]) if periods else None
    rules.append({"id":"T010","status":"triggered" if cr is not None and cash[-1]>0 and debt[-1]>0 else "unavailable" if cr is None else "not_triggered"})
    return {"metadata":{"periods":periods},"calculations":{"ocf_profit":vals if 'vals' in locals() else []},"rules":rules,"clusters":[],"gaps":gaps}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output"); a=ap.parse_args(); out=analyze(json.load(open(a.input)))
    text=json.dumps(out,ensure_ascii=False,indent=2); open(a.output,"w").write(text) if a.output else print(text)
if __name__=="__main__": main()
