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


def rank_relative_strength(values):
    """Percentile ranks on a 0-100 scale, averaging tied ordinal ranks."""
    series = pd.Series(values, dtype=float)
    if series.empty:
        return {}
    if len(series) == 1:
        return {str(series.index[0]): 100.0}
    ranked = (series.rank(method="average") - 1) / (len(series) - 1) * 100
    return {str(key): float(value) for key, value in ranked.items()}


def _trend(df):
    if len(df)<20:return "unavailable"
    ma=df.close.rolling(20).mean(); return "bullish" if df.close.iloc[-1]>ma.iloc[-1] and ma.iloc[-1]>ma.iloc[-5] else ("bearish" if df.close.iloc[-1]<ma.iloc[-1] and ma.iloc[-1]<ma.iloc[-5] else "neutral")


def multi_timeframe_state(df):
    def agg(rule): return df.resample(rule).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    states={"daily":_trend(df),"weekly":_trend(agg("W-FRI")),"monthly":_trend(agg("ME"))}
    vals={v for v in states.values() if v!="unavailable"}
    align="aligned_bullish" if vals=={"bullish"} else ("aligned_bearish" if vals=={"bearish"} else "conflicted")
    return {"states":states,"alignment":align}


def analyze_structure(df, bins=20):
    """ATR-aware pivots, price zones, volume profile, AVWAP and risk setup."""
    indicators = compute_indicators(df)
    atr = indicators.get("atr14") or float((df.high-df.low).tail(14).mean())
    pivots_low=[]; pivots_high=[]
    for i in range(2,len(df)-2):
        if df.low.iloc[i] == df.low.iloc[i-2:i+3].min() and df.high.iloc[i+1:].max()-df.low.iloc[i] >= atr:
            pivots_low.append(float(df.low.iloc[i]))
        if df.high.iloc[i] == df.high.iloc[i-2:i+3].max() and df.high.iloc[i]-df.low.iloc[i+1:].min() >= atr:
            pivots_high.append(float(df.high.iloc[i]))
    current=float(df.close.iloc[-1])
    def zones(points, side):
        points=sorted(points); groups=[]
        for point in points:
            if groups and abs(point-np.mean(groups[-1])) <= .5*atr: groups[-1].append(point)
            else: groups.append([point])
        vals=[{"price":float(np.mean(g)),"touches":len(g),"source":"atr_pivot"} for g in groups]
        return [x for x in vals if (x["price"]<current if side=="support" else x["price"]>current)]
    supports=zones(pivots_low,"support"); resistances=zones(pivots_high,"resistance")
    if not supports: supports=[{"price":float(df.low.tail(20).min()),"touches":1,"source":"20d_low"}]
    if not resistances: resistances=[{"price":float(df.high.tail(20).max()+2*atr),"touches":1,"source":"atr_target"}]
    edges=np.linspace(float(df.close.min()),float(df.close.max())+1e-12,bins+1); ids=np.clip(np.digitize(df.close,edges)-1,0,bins-1)
    profile=[{"low":float(edges[i]),"high":float(edges[i+1]),"volume":float(df.volume[ids==i].fillna(0).sum())} for i in range(bins)]
    anchor_candidates=[i for i in range(2,len(df)-2) if df.low.iloc[i]==df.low.iloc[i-2:i+3].min()]; anchor=anchor_candidates[-1] if anchor_candidates else max(0,len(df)-60)
    typical=(df.high+df.low+df.close)/3; avwap=float((typical.iloc[anchor:]*df.volume.iloc[anchor:]).sum()/df.volume.iloc[anchor:].sum())
    entry=current; invalid=max(x["price"] for x in supports); target=min(x["price"] for x in resistances)
    risk=max(entry-invalid,.5*atr); reward=max(target-entry,0); rr=reward/risk
    if rr<1.5: target=entry+1.5*risk; rr=1.5
    gaps=[]
    for i in range(1,len(df)):
        if df.low.iloc[i]>df.high.iloc[i-1]: gaps.append({"date":df.index[i],"type":"up","low":float(df.high.iloc[i-1]),"high":float(df.low.iloc[i])})
        elif df.high.iloc[i]<df.low.iloc[i-1]: gaps.append({"date":df.index[i],"type":"down","low":float(df.high.iloc[i]),"high":float(df.low.iloc[i-1])})
    return json_safe({"supports":supports,"resistances":resistances,"gaps":gaps,"volume_profile":profile,"anchored_vwap":avwap,"setup":{"entry_zone":[entry-.25*atr,entry+.25*atr],"invalidation":invalid,"targets":[target],"risk_reward":rr}})


def compute_breadth(quotes: Iterable[dict], previous_ad_line=0.0):
    q=list(quotes); up=sum(x.get("pct_chg",0)>0 for x in q); down=sum(x.get("pct_chg",0)<0 for x in q); flat=len(q)-up-down
    above20=sum(x.get("ma20") is not None and x.get("close",0)>x["ma20"] for x in q); above60=sum(x.get("ma60") is not None and x.get("close",0)>x["ma60"] for x in q)
    nh20=sum(x.get("high20") is not None and x.get("close")>=x["high20"] for x in q); nl20=sum(x.get("low20") is not None and x.get("close")<=x["low20"] for x in q)
    return {"schema_version":"2.0","participation":{"advancers":up,"decliners":down,"unchanged":flat,"advance_ratio":up/len(q) if q else None,"ad_line":previous_ad_line+up-down},"moving_average_breadth":{"above_ma20":above20/len(q) if q else None,"above_ma60":above60/len(q) if q else None},"new_highs_lows":{"new_high_20":nh20,"new_low_20":nl20}}


def calibrate_signals(df, signals, horizons=(1,3,5,10,20), min_history=250):
    if len(df)<min_history:return {"status":"insufficient_data","source_bars":len(df)}
    groups={}
    for h in horizons:
        vals=[]; maes=[]; mfes=[]; last=-h
        for i in sorted(set(signals)):
            if i-last<h or i+h>=len(df): continue
            entry=df.close.iloc[i]; path=df.iloc[i+1:i+h+1]; vals.append(df.close.iloc[i+h]/entry-1)
            maes.append(float(path.low.min()/entry-1)); mfes.append(float(path.high.max()/entry-1)); last=i
        wins=[x for x in vals if x>0]; losses=[x for x in vals if x<=0]
        payoff=(np.mean(wins)/abs(np.mean(losses))) if wins and losses and np.mean(losses) else None
        groups[str(h)]={"sample_size":len(vals),"win_rate":sum(x>0 for x in vals)/len(vals) if vals else None,"mean_return":float(np.mean(vals)) if vals else None,"median_return":float(np.median(vals)) if vals else None,"expected_return":float(np.mean(vals)) if vals else None,"mae":float(np.mean(maes)) if maes else None,"mfe":float(np.mean(mfes)) if mfes else None,"payoff_ratio":float(payoff) if payoff is not None else None,"confidence":"low" if len(vals)<30 else "normal"}
    return json_safe({"status":"available","source_bars":len(df),"horizons":groups})


def analyze_ah_pair(a,h,fx,as_of,max_fx_age_days=3):
    common=a.index.intersection(h.index).intersection(fx.index); eligible=common[common<=pd.Timestamp(as_of)]
    if len(eligible)==0:return {"status":"unavailable","reason":"fx_missing"}
    d=eligible[-1]
    if (pd.Timestamp(as_of)-d).days>max_fx_age_days:return {"status":"unavailable","reason":"fx_stale"}
    premiums=(a.loc[eligible,"close"]/(h.loc[eligible,"close"]*fx.loc[eligible])-1)*100; cur=float(premiums.iloc[-1]); sd=premiums.tail(60).std(ddof=0)
    return json_safe({"status":"available","as_of":d,"fx_rate":float(fx.loc[d]),"premium_pct":cur,"mean_60":float(premiums.tail(60).mean()),"zscore_60":float((cur-premiums.tail(60).mean())/sd) if sd else None,"percentile_60":float((premiums.tail(60)<=cur).mean())})


def analyze_cross_asset(stock, driver, windows=(20,60), max_lag=5):
    joined=pd.concat([stock.rename("stock"),driver.rename("driver")],axis=1,join="inner").dropna()
    if len(joined)<max(windows): return {"status":"insufficient_data","observations":len(joined)}
    returns=joined.pct_change().dropna(); out={"status":"available","observations":len(returns)}
    for w in windows:
        sample=returns.tail(w); out[f"correlation_{w}"]=float(sample.stock.corr(sample.driver)); var=sample.driver.var(ddof=0); out[f"beta_{w}"]=float(sample.stock.cov(sample.driver,ddof=0)/var) if var else None
    correlations={lag:float(joined.stock.corr(joined.driver.shift(lag))) for lag in range(-max_lag,max_lag+1)}
    out["best_lag"]=max(correlations,key=lambda k: correlations[k] if math.isfinite(correlations[k]) else -2); out["lead_lag_correlations"]={str(k):v for k,v in correlations.items()}
    sample=returns.tail(max(windows)); beta=out[f"beta_{max(windows)}"]; residual=sample.stock-beta*sample.driver; sd=residual.std(ddof=0); out["divergence_zscore"]=float((residual.iloc[-1]-residual.mean())/sd) if sd else None
    return json_safe(out)


def analyze_portfolio(positions, return_series, annualization=252,var_level=.95):
    values={p["code"]:p["shares"]*p["price"] for p in positions}; total=sum(values.values()); weights={k:v/total for k,v in values.items()}; w=pd.Series(weights)
    cols=[c for c in w.index if c in return_series]; r=return_series[cols].dropna(); ww=w[cols]; pr=r.dot(ww); vol=float(pr.std(ddof=0)*np.sqrt(annualization)) if len(pr) else None
    curve=(1+pr).cumprod(); dd=curve/curve.cummax()-1 if len(curve) else pd.Series(dtype=float)
    stress=sum(max(0,(p["price"]-p.get("stop",p["price"]))*p["shares"]) for p in positions)
    component={}
    if len(r) and vol:
        cov=r.cov(ddof=0)*annualization; variance=float(ww.values@cov.values@ww.values); sigma=math.sqrt(variance)
        marginal=cov.values@ww.values/sigma; component={code:float(ww.iloc[i]*marginal[i]) for i,code in enumerate(cols)}
    sector={}; theme={}
    for p in positions:
        sector[p.get("sector","unknown")]=sector.get(p.get("sector","unknown"),0)+weights[p["code"]]
        theme[p.get("theme","unknown")]=theme.get(p.get("theme","unknown"),0)+weights[p["code"]]
    return json_safe({"schema_version":"2.0","weights":weights,"correlation":r.corr().to_dict(),"annualized_volatility":vol,"component_risk":component,"max_drawdown":float(dd.min()) if len(dd) else None,"historical_var_95":float(max(0,-pr.quantile(1-var_level))) if len(pr) else None,"stop_stress_loss":stress,"sector_exposure":sector,"theme_exposure":theme})
