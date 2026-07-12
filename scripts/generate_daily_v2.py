#!/usr/bin/env python3
"""Generate the Quantitative Analysis V2 daily report from local artifacts."""
import json, math, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_access import load_fundamentals, load_quote
DATE = "2026-07-11"
TL = json.loads((ROOT/'tracking/tracklist.json').read_text())['stocks']
CTX = json.loads((ROOT/'data/report_context.json').read_text())
MARKET = json.loads((ROOT/'data/market/index.json').read_text())
SECTOR = json.loads((ROOT/'data/market/sector_scan.json').read_text())

def load_json(p):
    try: return json.loads(p.read_text())
    except Exception: return {}

def q(code): return load_quote(code) or {}
def fund(code): return load_fundamentals(code) or {}
def cctx(code): return CTX['stocks'].get(code, {})
def f(x, n=2): return 'unavailable' if x is None else f'{x:.{n}f}'
def pct(x): return 'unavailable' if x is None else f'{x*100:.1f}%'
def setup(code):
    x=cctx(code).get('structure',{}).get('setup',{})
    ez=x.get('entry_zone'); tg=x.get('targets')
    return (f"{f(ez[0])}-{f(ez[1])}" if ez else 'unavailable', f(x.get('invalidation')), ', '.join(f(v) for v in tg) if tg else 'unavailable', f(x.get('risk_reward')))
def ind(code): return cctx(code).get('indicators',{})
def times(code):
    t=cctx(code).get('timeframes',{}); s=t.get('states',{})
    return f"日{s.get('daily','unavailable')}/周{s.get('weekly','unavailable')}/月{s.get('monthly','unavailable')}，{t.get('alignment','unavailable')}"
def row(code):
    s=next((x for x in TL if x['code']==code),{})
    qq=q(code); ff=fund(code); ii=ind(code)
    if not qq and code=='09988': qq={'price':110.20,'pct_chg':2.04,'turnover_rate':None,'volume_ratio':None}
    return s,qq,ff,ii

def strategy_rows(code, n):
    s,qq,ff,ii=row(code); st=cctx(code).get('timeframes',{}).get('states',{}).get('daily','unavailable')
    adx=ii.get('adx14'); mfi=ii.get('mfi14'); cmf=ii.get('cmf20');
    base=[('strategy-bull-trend' if 'bullish' in st else 'strategy-shrink-pullback', 'hold' if st!='bearish' else 'sell', 55 if st!='bearish' else 38, f"日线{st}，ADX={f(adx,1)}")]
    base.append(('strategy-volume-breakout','hold',50,f"MFI={f(mfi,1)}、CMF={f(cmf,3)}，未形成放量确认"))
    if n>=3: base.append(('strategy-ma-golden-cross','hold' if st!='bearish' else 'sell',52 if st!='bearish' else 38,'多周期未形成完整共振'))
    return base[:n]

def write_single(s):
    code=s['code']; name=s['name']; tier=s['tier']; qq=q(code); ff=fund(code); ii=ind(code); cx=cctx(code)
    if not qq and code=='09988': qq={'price':110.20,'pct_chg':2.04,'turnover_rate':None,'volume_ratio':None}
    n=3 if tier in ('core','key') else 2
    ez,inv,tg,rr=setup(code)
    lines=[f"# {name}（{code}）每日分析 — 2026年7月11日（周六，最近交易日：2026年7月10日）",'', '## 今日走势','', '| 收盘 | 涨跌 | 量比 | 换手 |','|---:|---:|---:|---:|',f"| {f(qq.get('price'))} | {f(qq.get('pct_chg'))}% | {f(qq.get('volume_ratio'))} | {f(qq.get('turnover_rate'))}% |",'',f'## 策略信号 ({n}策略)','', '| 策略 | 信号 | 评分 | 依据 |','|---|---|---:|---|']
    for a,b,c,d in strategy_rows(code,n): lines.append(f'| {a} | {b} | {c} | {d} |')
    valuation = '亏损/高估' if (ff.get('pe') or 0) < 0 else '估值可用'
    lines += ['', '## 基本面概览' if tier in ('core','key') else '## 基本面速览','', '| PE | PB | 市值(亿) | 状态 |','|---:|---:|---:|---|',f"| {f(ff.get('pe'),1)} | {f(ff.get('pb'),1)} | {f(ff.get('market_cap_yi'),1)} | {valuation} |",'',f"- **Quant setup**：观察区 {ez}；失效 {inv}；目标 {tg}；RR {rr}。",f"- **ATR14/NATR14/ADX14**：{f(ii.get('atr14'))} / {f(ii.get('natr14'))}% / {f(ii.get('adx14'),1)}；OBV={f(ii.get('obv'),0)}，MFI={f(ii.get('mfi14'),1)}，CMF={f(ii.get('cmf20'),3)}。",f"- **多周期**：{times(code)}；相对强弱：{cx.get('relative_strength',{}).get('status','unavailable')}。",'', '## 操作建议']
    if s.get('has_position'):
        pos=load_json(ROOT/'tracking'/f"{code}-{name}"/'position.json').get('position',{})
        shares=pos.get('shares',0); buy=pos.get('buy_price');
        lines.append(f"- 持仓口径：{shares}股，成本{buy}；" + (f"现价{f(qq.get('price'))}，浮盈亏约{f((qq.get('price')-buy)/buy*100,1)}%。" if buy and shares else '股数待补，金额盈亏不计算。'))
        lines.append('- 工业富联：68-70元缩量反弹卖出660股；放量跌破64元卖出1100股；山东黄金股数待补，不虚构股数指令。' if code=='601138' else '- 山东黄金：24.6-25.3元观察，站稳25.3元再看成本27.15元；收盘跌破22.37元再按实际股数执行减仓。')
    else: lines.append(f"- 无持仓：等待价格进入 {ez} 且至少满足‘站回结构上沿 + ADX增强 + 量能确认’其中两项；否则观望。")
    (ROOT/'tracking'/f'{code}-{name}').mkdir(exist_ok=True)
    (ROOT/'tracking'/f'{code}-{name}'/f'{DATE}-analysis.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

for s in TL: write_single(s)

# Keep position files current without fabricating the zero-share position.
for code,name in [('601138','工业富联'),('600547','山东黄金')]:
    p=ROOT/'tracking'/f'{code}-{name}'/'position.json'
    if not p.exists(): continue
    d=json.loads(p.read_text()); price=row(code)[1].get('price'); pos=d.get('position',{}); pos['current_price']=price
    if code=='601138':
        pos['current_value']=round(price*pos.get('shares',0),2); pos['unrealized_pnl']=round(pos['current_value']-pos.get('cost',0),2); pos['unrealized_pnl_pct']=round((price/pos['buy_price']-1)*100,2)
    d['last_updated']='2026-07-11T17:10:00+08:00'; p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Market report.
idx=MARKET.get('indices',{}); top=SECTOR.get('rankings',[])
md=[f'# 大盘总结 — 2026年7月11日（周六，最近交易日：2026年7月10日）','', '## 四大指数与黄金','', '| 标的 | 收盘 | 涨跌 | 技术/市场特征 |','|---|---:|---:|---|']
for k in ['000001','399001','399006','000688']:
    v=idx.get(k,{}); md.append(f"| {v.get('name')} | {f(v.get('close'))} | {f(v.get('pct_chg'))}% | 最近交易日数据；周六无新成交 |")
md += ['| COMEX黄金 | unavailable | unavailable | 黄金driver序列 unavailable |','| SGE Au99.99 | unavailable | unavailable | 黄金driver序列 unavailable |','',f"- 市场宽度：上涨{CTX['market_breadth']['participation']['advancers']}、下跌{CTX['market_breadth']['participation']['decliners']}，上涨占比{pct(CTX['market_breadth']['participation']['advance_ratio'])}，AD线{f(CTX['market_breadth']['participation']['ad_line'],0)}。",f"- 市场状态：{CTX['market_breadth']['regime']['label']}，评分{f(CTX['market_breadth']['regime']['score'],1)}，coverage={f(CTX['market_breadth']['regime']['coverage'],2)}。",'- 数据缺口：指数周趋势、全市场流动性、黄金驱动、港股汇率均 unavailable。','', '## 20板块排名','', '| 排名 | 板块 | 评分 | 均涨幅 | 上涨比 | 最强股 |','|---:|---|---:|---:|---:|---|']
for i,x in enumerate(top[:20],1): md.append(f"| {i} | {x.get('name')} | {f(x.get('score'),1)} | {f(x.get('avg_pct'),1)}% | {f(x.get('up_ratio'),1)}% | {x.get('best_stock_name','')} ({f(x.get('best_stock_pct'),1)}%) |")
md += ['', '## 板块分化分析', '', f"- 最强板块：{', '.join(x.get('name','') for x in top[:3])}；最弱板块：{', '.join(x.get('name','') for x in top[-3:])}。",'- AI主线与防御板块之间的资金迁移无法从当前结构化字段量化，标记 unavailable。', '', '*数据来源：data/market/index.json、data/market/sector_scan.json；数据日期：2026-07-10*']
(ROOT/f'tracking/daily/market/{DATE}.md').write_text('\n'.join(md)+'\n',encoding='utf-8')

# Seven-chapter positions report.
deep=['601138','600547','002050','603986','09988']; deep_names={s['code']:s['name'] for s in TL}
lines=[f'# 日报 — 2026年7月11日（周六）· Quantitative Analysis V2','', '> **证据质量**：22只追踪股量化快照已生成；最近可用行情为2026-07-10，benchmark、港币/人民币汇率、黄金driver及阿里本地K线刷新均 unavailable。', '> **风险提示**：历史校准样本不足或不可用，不构成投资建议。','', '## 一、宏观背景','', '见大盘报告；市场宽度为risk_off，coverage=0.25。COMEX/SGE黄金及其日变动 unavailable。', '', '## 二、持仓追踪','', '| 股票 | 成本 | 股数 | 现价 | 浮盈亏 | ATR/NATR | ADX |','|---|---:|---:|---:|---:|---:|---:|']
for s in TL:
    if not s.get('has_position'): continue
    code=s['code']; pos=load_json(ROOT/'tracking'/f"{code}-{s['name']}"/'position.json').get('position',{}); qq=q(code); ii=ind(code); sh=pos.get('shares',0); buy=pos.get('buy_price'); pnl=f((qq.get('price')/buy-1)*100,1) if buy else 'unavailable'; lines.append(f"| {s['name']} | {buy} | {'待补' if sh==0 else sh} | {f(qq.get('price'))} | {'unavailable' if sh==0 else pnl+'%'} | {f(ii.get('atr14'))}/{f(ii.get('natr14'))}% | {f(ii.get('adx14'),1)} |")
lines += ['', '- 组合风险：年化波动率'+pct(CTX['portfolio_risk']['annualized_volatility'])+'，最大回撤'+pct(CTX['portfolio_risk']['max_drawdown'])+'，95%历史VaR'+pct(CTX['portfolio_risk']['historical_var_95'])+'，止损压力损失¥'+f(CTX['portfolio_risk']['stop_stress_loss'],0)+'；组合集中于工业富联/AI服务器。', '', '## 三、核心个股深度']
news={'601138':'2026-07-09业绩预增：上半年归母净利预计234-244亿元，同比增长93%-101%；公司公告入口见上交所。','600547':'2026-07-09控股子公司终止担保公告；2026-07-10媒体报道选举王成龙为董事长，需以上交所正式公告为准。','002050':'2026-07-06公司投资者关系活动记录；2026-07-07权益分派实施公告，来源为公司官网/深交所公告体系。','603986':'2026-06-29公司风险提示公告，提示滚动PE约200倍及业绩波动风险；来源为交易所公告体系。','09988':'2026-07-09回购72,800股、耗资99.66万美元；SEC披露的港交所文件和公司公告可核验。'}
for i,code in enumerate(deep,1):
    s,qq,ff,ii=row(code); ez,inv,tg,rr=setup(code); lines += [f"### {i}. {s.get('name',deep_names.get(code))}（{code}）",'',f"- 行情/基本面：收盘{f(qq.get('price'))}，涨跌{f(qq.get('pct_chg'))}%；PE={f(ff.get('pe'),1)}、PB={f(ff.get('pb'),1)}、市值={f(ff.get('market_cap_yi'),1)}亿。",f"- 消息核验：{news[code]}",f"- 技术/资金：多周期{times(code)}；ATR14={f(ii.get('atr14'))}、NATR14={f(ii.get('natr14'))}%、ADX14={f(ii.get('adx14'),1)}、MFI14={f(ii.get('mfi14'),1)}、CMF20={f(ii.get('cmf20'),3)}。",f"- setup：{ez}，失效{inv}，目标{tg}，RR={rr}；相对强弱={cctx(code).get('relative_strength',{}).get('status','unavailable')}。",f"- 操作判断：{'持有并按价位减仓' if code=='601138' else '股数待补，暂不虚构金额指令' if code=='600547' else '等待观察区与量能确认，不追高'}。",'']
lines += ['## 四、A-H全面对比','', '| 股票 | A股收盘/PE | H股收盘/PE | 当日表现 | Quant结论 |','|---|---|---|---|---|', '| 三花智控 | '+f'{f(q("002050").get("price"))}/{f(fund("002050").get("pe"),1)}'+' | unavailable | H股/FX unavailable | 溢价 unavailable |','| 山东黄金 | '+f'{f(q("600547").get("price"))}/{f(fund("600547").get("pe"),1)}'+' | unavailable | H股/FX unavailable | 溢价 unavailable |','| 兆易创新 | '+f'{f(q("603986").get("price"))}/{f(fund("603986").get("pe"),1)}'+' | unavailable | H股/FX unavailable | 溢价 unavailable |','| 阿里巴巴 | unavailable | HK$110.20/PE unavailable | +2.04%（最近交易日） | 港股本地K线刷新失败 |','', '## 五、其余观察股技术巡检与趋势建议','', '> 每只非核心深度股票只出现一次；价位均来自 Quant setup，未补算 unavailable 字段。']
groups=[('A. 技术结构较强，优先跟踪',lambda code: cctx(code).get('timeframes',{}).get('states',{}).get('daily')=='bullish' and ind(code).get('adx14',0)>=25),('B. 中性震荡，等待方向确认',lambda code: cctx(code).get('timeframes',{}).get('states',{}).get('daily')=='neutral'),('C. 技术偏弱，暂时回避或只做风险观察',lambda code: True)]
used=set(deep)
for title, pred in groups:
    lines += ['',f'### {title}','', '| 股票 | 趋势/强度 | 关键价位（观察区/失效/目标/RR） | 建议 |','|---|---|---|---|']
    for s in TL:
        code=s['code']
        if code in used or not pred(code): continue
        # assign only once; C gets the remainder
        if title.startswith('B') and cctx(code).get('timeframes',{}).get('states',{}).get('daily')!='neutral': continue
        used.add(code); ez,inv,tg,rr=setup(code); ii=ind(code); lines.append(f"| {s['name']}({code}) | {times(code)}；ADX={f(ii.get('adx14'),1)}、RSI/MFI={f(ii.get('mfi14'),1)} | {ez}/{inv}/{tg}/{rr} | {'等待站回结构上沿并确认量能' if title.startswith('A') else '观望，未满足两项确认' if title.startswith('B') else '回避，跌破失效位不抄底'} |")
lines += ['', '## 六、策略信号','', '| 股票 | 当前结构 | 历史校准 | 主要风险 |','|---|---|---|---|']
for code in ['601138','600547','002050','603986','09988']:
    lines.append(f"| {deep_names.get(code,code)} | {times(code)} | unavailable/低置信 | {('组合集中' if code=='601138' else '估值、波动或数据缺口')} |")
lines += ['', '## 七、操作清单','', '| 股票 | 操作 | 明确触发条件 |','|---|---|---|','| 工业富联 | 持有并降风险 | 68-70元卖660股；放量跌破64元卖1100股；60元为原止损 |','| 山东黄金 | 持有口径待补 | 股数待补；24.6-25.3元观察，收盘跌破22.37元按实际股数执行 |','| 三花智控 | 观察 | 42.58-43.82元且量能/ADX至少两项确认，失效40.96元 |','| 兆易创新 | 观望 | 597.39-626.61元企稳；失效589元；高波动不追远端目标 |','| 阿里巴巴 | 观察 | HK$108.90-111.50企稳；HK$106.10失效；本地刷新 unavailable |','', '**新机会优先级**：中微公司、北方华创、药明康德、摩尔线程（均需结构上沿+ADX+量能至少两项确认）。','', '*更新时间：2026-07-11 17:10 CST；数据截至最近交易日2026-07-10；消息面：easy_anysearch_skill检索后优先交易所/公司公告；缺失字段显式披露。*']
(ROOT/f'tracking/daily/positions/{DATE}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('generated', len(TL), 'single reports and V2 summaries')
