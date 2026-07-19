# 日报 — {{date}}（{{weekday}}）· Quantitative Analysis V2

> **证据质量**：{{data_coverage}}

> **风险提示**：本报告是基于历史行情的决策支持，不构成投资建议。校准样本不足30次时必须标记低置信。

## 一、宏观背景

### 四大指数与黄金

| 标的 | 收盘 | 涨跌 | 技术/市场特征 |
|---|---:|---:|---|
| 上证指数 | {{close}} | {{pct}} | {{state}} |
| 深证成指 | {{close}} | {{pct}} | {{state}} |
| 创业板指 | {{close}} | {{pct}} | {{state}} |
| 科创50 | {{close}} | {{pct}} | {{state}} |
| COMEX黄金 | {{price}} | {{pct_or_unavailable}} | {{state}} |
| SGE Au99.99 | {{price}} | {{pct_or_unavailable}} | {{state}} |

- **市场宽度**：{{breadth}}
- **市场状态**：{{regime_and_coverage}}
- **板块TOP5**：{{sector_top5}}
- **数据缺口**：{{unavailable_fields}}

## 二、持仓追踪

> 遍历 `tracklist.json` 中所有 `has_position=true` 股票。必须再读取 `position.json`；不得因 `shares=0` 自动断定无持仓，应披露股数待补。

### {{name}}（{{code}}）

| 成本 | 股数 | 现价 | 市值 | 浮盈亏 | ATR/NATR | ADX |
|---:|---:|---:|---:|---:|---:|---:|
| {{buy_price}} | {{shares_or_pending}} | {{price}} | {{value_or_pending}} | {{pnl}} | {{atr_natr}} | {{adx}} |

- **多周期**：{{daily_weekly_monthly_alignment}}
- **量价资金**：{{obv_mfi_cmf}}
- **价量结构**：量比 {{intraday_volume_ratio}} / 当日量÷MA5 {{volume_vs_ma5}} / 当日量÷MA20 {{volume_vs_ma20}} / 近20日÷前20日 {{recent20_vs_previous20}} / 上涨日÷下跌日均量 {{up_down_volume_ratio_90d}}；MFI {{mfi14}} / CMF {{cmf20}} / OBV20 {{obv_20d_direction}}；{{price_volume_label_and_interpretation}}
- **Quant setup**：{{entry_zone}} / 失效 {{invalidation}} / 目标 {{targets}} / RR {{risk_reward}}
- **操作指令**：{{exact_price_volume_action}}

### 组合风险

{{portfolio_volatility_drawdown_var_concentration_stop_stress}}

## 三、核心个股深度

> 固定覆盖工业富联、山东黄金、三花智控、兆易创新、阿里巴巴。消息面先用 `easy_anysearch_skill`，再优先核验交易所/公司公告，保留日期与链接。

### {{index}}. {{name}}（{{code}}）

- **持仓/行情**：{{position_and_quote}}
- **消息核验**：{{dated_news_with_source_links}}
- **技术面**：{{atr_adx_bollinger_timeframes}}
- **资金面**：{{obv_mfi_cmf}}
- **价量结构**：量比 {{intraday_volume_ratio}} / 当日量÷MA5 {{volume_vs_ma5}} / 当日量÷MA20 {{volume_vs_ma20}} / 近20日÷前20日 {{recent20_vs_previous20}} / 上涨日÷下跌日均量 {{up_down_volume_ratio_90d}}；MFI {{mfi14}} / CMF {{cmf20}} / OBV20 {{obv_20d_direction}}；{{price_volume_label_and_interpretation}}
- **setup**：{{entry_zone}}，失效 {{invalidation}}，目标 {{targets}}，RR {{risk_reward}}
- **历史校准**：{{calibration_or_insufficient_data}}
- **操作判断**：{{specific_action}}

## 四、A-H全面对比

| 股票 | A股收盘/PE | H股收盘/PE | 当日表现 | Quant结论 |
|---|---|---|---|---|
| {{name}} | {{a_quote}} | {{h_quote}} | {{performance}} | {{premium_or_unavailable}} |

> 没有对应日期 HKD/CNY 时，A/H溢价必须写 `unavailable`，不得直接比较两种货币价格。

## 五、其余观察股技术巡检与趋势建议

> 本章必须覆盖 `tracklist.json` 中除核心深度股外的所有股票，每只只出现一次。

### A. 技术结构较强，优先跟踪

| 股票 | 趋势/强度 | 关键价位（观察区/失效/目标） | 建议 |
|---|---|---|---|
| {{name}} | {{timeframes_adx_rsi}} | {{entry_invalidation_target}} | {{action}} |

### B. 中性震荡，等待方向确认

| 股票 | 趋势/强度 | 关键价位（观察区/失效/目标） | 建议 |
|---|---|---|---|
| {{name}} | {{timeframes_adx_rsi}} | {{entry_invalidation_target}} | {{action}} |

### C. 技术偏弱，暂时回避或只做风险观察

| 股票 | 趋势/强度 | 关键价位（观察区/失效/目标） | 建议 |
|---|---|---|---|
| {{name}} | {{timeframes_adx_rsi}} | {{entry_invalidation_target}} | {{action}} |

> 分组原则：日周多头共振优先归A；多周期冲突或中性归B；日线空头、结构破位或风险无法控制归C。不得因单日大跌直接建议抄底。

## 六、策略信号

| 股票 | 当前结构 | 历史校准 | 主要风险 |
|---|---|---|---|
| {{name}} | {{structure}} | {{calibration}} | {{risk}} |

> 历史胜率是事件研究结果，不是未来上涨概率。

## 七、操作清单

| 股票 | 操作 | 明确触发条件 |
|---|---|---|
| {{position_name}} | {{hold_reduce_exit}} | {{price_volume_and_shares}} |

**新机会跟踪优先级**：{{ranked_watchlist}}

**入场确认原则**：“站回结构上沿 + ADX增强 + 量能确认”三项中至少满足两项。

---

*更新时间：{{generated_at}} · 数据：{{sources}}/Quantitative Analysis V2 · 消息面：easy_anysearch_skill检索后优先使用交易所/公司公告 · {{evidence_gaps}}*
