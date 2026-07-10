"""Auditable quantitative calculations with no I/O or network access."""
from __future__ import annotations
import math
from typing import Iterable
import numpy as np
import pandas as pd
from .models import json_safe


def _last(s):
    v = s.iloc[-1] if len(s) else np.nan
    return None if pd.isna(v) or not math.isfinite(float(v)) else float(v)


def compute_indicators(df: pd.DataFrame) -> dict:
    h,l,c,v=df.high,df.low,df.close,df.volume
    prev=c.shift(1); tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    up=h.diff(); down=-l.diff(); plus=up.where((up>down)&(up>0),0.0); minus=down.where((down>up)&(down>0),0.0)
    pdi=100*plus.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr.replace(0,np.nan)
    mdi=100*minus.ewm(alpha=1/14,adjust=False,min_periods=14).mean()/atr.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan); adx=dx.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    ma=c.rolling(20).mean(); sd=c.rolling(20).std(ddof=0); upper=ma+2*sd; lower=ma-2*sd
    obv=(np.sign(c.diff()).fillna(0)*v.fillna(0)).cumsum()
    tp=(h+l+c)/3; flow=tp*v; pos=flow.where(tp.diff()>0,0).rolling(14).sum(); neg=flow.where(tp.diff()<0,0).rolling(14).sum().abs()
    mfi=100-100/(1+pos/neg.replace(0,np.nan)); mfv=((c-l)-(h-c))/(h-l).replace(0,np.nan)*v
    cmf=mfv.rolling(20).sum()/v.rolling(20).sum().replace(0,np.nan)
    rv=np.log(c/c.shift()).rolling(20).std(ddof=0)*np.sqrt(252)
    return json_safe({"atr14":_last(atr),"natr14":_last(100*atr/c),"adx14":_last(adx),"plus_di14":_last(pdi),"minus_di14":_last(mdi),
      "bb_upper":_last(upper),"bb_middle":_last(ma),"bb_lower":_last(lower),"bb_width":_last((upper-lower)/ma),"bb_percent_b":_last((c-lower)/(upper-lower)),
      "obv":_last(obv),"mfi14":_last(mfi.fillna(100)),"cmf20":_last(cmf),"realized_vol20":_last(rv)})


def relative_strength(stock, benchmark, windows=(5,20,60)):
    joined=pd.concat([stock.close.rename("s"),benchmark.close.rename("b")],axis=1,join="inner").dropna(); out={"observations":len(joined)}
    ret=joined.pct_change().dropna()
    for w in windows:
        if len(joined)>w:
            sr=joined.s.iloc[-1]/joined.s.iloc[-w-1]-1; br=joined.b.iloc[-1]/joined.b.iloc[-w-1]-1
            out.update({f"return_{w}":float(sr),f"benchmark_return_{w}":float(br),f"relative_{w}":float(sr-br)})
            r=ret.tail(w); var=r.b.var(ddof=0); out[f"beta_{w}"]=float(r.s.cov(r.b,ddof=0)/var) if var else None; out[f"correlation_{w}"]=float(r.s.corr(r.b))
    return json_safe(out)


def _trend(df):
    if len(df)<20:return "unavailable"
    ma=df.close.rolling(20).mean(); return "bullish" if df.close.iloc[-1]>ma.iloc[-1] and ma.iloc[-1]>ma.iloc[-5] else ("bearish" if df.close.iloc[-1]<ma.iloc[-1] and ma.iloc[-1]<ma.iloc[-5] else "neutral")


def multi_timeframe_state(df):
    def agg(rule): return df.resample(rule).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    states={"daily":_trend(df),"weekly":_trend(agg("W-FRI")),"monthly":_trend(agg("ME"))}
    vals={v for v in states.values() if v!="unavailable"}
    align="aligned_bullish" if vals=={"bullish"} else ("aligned_bearish" if vals=={"bearish"} else "conflicted")
    return {"states":states,"alignment":align}


def compute_breadth(quotes: Iterable[dict], previous_ad_line=0.0):
    q=list(quotes); up=sum(x.get("pct_chg",0)>0 for x in q); down=sum(x.get("pct_chg",0)<0 for x in q); flat=len(q)-up-down
    above20=sum(x.get("ma20") is not None and x.get("close",0)>x["ma20"] for x in q); above60=sum(x.get("ma60") is not None and x.get("close",0)>x["ma60"] for x in q)
    nh20=sum(x.get("high20") is not None and x.get("close")>=x["high20"] for x in q); nl20=sum(x.get("low20") is not None and x.get("close")<=x["low20"] for x in q)
    return {"schema_version":"2.0","participation":{"advancers":up,"decliners":down,"unchanged":flat,"advance_ratio":up/len(q) if q else None,"ad_line":previous_ad_line+up-down},"moving_average_breadth":{"above_ma20":above20/len(q) if q else None,"above_ma60":above60/len(q) if q else None},"new_highs_lows":{"new_high_20":nh20,"new_low_20":nl20}}


def calibrate_signals(df, signals, horizons=(1,3,5,10,20), min_history=250):
    if len(df)<min_history:return {"status":"insufficient_data","source_bars":len(df)}
    groups={}
    for h in horizons:
        vals=[]
        for i in signals:
            if i+h<len(df): vals.append(df.close.iloc[i+h]/df.close.iloc[i]-1)
        groups[str(h)]={"sample_size":len(vals),"win_rate":sum(x>0 for x in vals)/len(vals) if vals else None,"mean_return":float(np.mean(vals)) if vals else None,"median_return":float(np.median(vals)) if vals else None}
    return json_safe({"status":"available","source_bars":len(df),"horizons":groups})


def analyze_ah_pair(a,h,fx,as_of,max_fx_age_days=3):
    common=a.index.intersection(h.index).intersection(fx.index); eligible=common[common<=pd.Timestamp(as_of)]
    if len(eligible)==0:return {"status":"unavailable","reason":"fx_missing"}
    d=eligible[-1]
    if (pd.Timestamp(as_of)-d).days>max_fx_age_days:return {"status":"unavailable","reason":"fx_stale"}
    premiums=(a.loc[eligible,"close"]/(h.loc[eligible,"close"]*fx.loc[eligible])-1)*100; cur=float(premiums.iloc[-1]); sd=premiums.tail(60).std(ddof=0)
    return json_safe({"status":"available","as_of":d,"fx_rate":float(fx.loc[d]),"premium_pct":cur,"mean_60":float(premiums.tail(60).mean()),"zscore_60":float((cur-premiums.tail(60).mean())/sd) if sd else None,"percentile_60":float((premiums.tail(60)<=cur).mean())})


def analyze_portfolio(positions, return_series, annualization=252,var_level=.95):
    values={p["code"]:p["shares"]*p["price"] for p in positions}; total=sum(values.values()); weights={k:v/total for k,v in values.items()}; w=pd.Series(weights)
    cols=[c for c in w.index if c in return_series]; r=return_series[cols].dropna(); ww=w[cols]; pr=r.dot(ww); vol=float(pr.std(ddof=0)*np.sqrt(annualization)) if len(pr) else None
    curve=(1+pr).cumprod(); dd=curve/curve.cummax()-1 if len(curve) else pd.Series(dtype=float)
    stress=sum(max(0,(p["price"]-p.get("stop",p["price"]))*p["shares"]) for p in positions)
    return json_safe({"schema_version":"2.0","weights":weights,"correlation":r.corr().to_dict(),"annualized_volatility":vol,"max_drawdown":float(dd.min()) if len(dd) else None,"historical_var_95":float(max(0,-pr.quantile(1-var_level))) if len(pr) else None,"stop_stress_loss":stress})
