---
name: daily-report
description: 每日追踪报告 — 生成单文件七章大盘、持仓、核心个股与观察股报告，并发布 HTML
---

# 每日追踪报告

执行登记的 `daily-report` 工作流。唯一 Markdown 交付物是 `artifact.daily_report`：

`tracking/daily/positions/YYYY-MM-DD.md`

不得另写大盘 Markdown、逐股 Markdown 或按 tier 固定数量的报告。HTML 是 `$deploy` 从该 Markdown 生成的发布产物，不是第二份分析源文件。

## 前置与证据

1. 运行 `source .venv/bin/activate && python scripts/fetch_all_daily.py`，读取 `tracking/tracklist.json` 获取当前全部追踪股，不假设数量。
2. 运行 `python scripts/run_quant_analysis.py --date YYYY-MM-DD`，在任何定量结论前读取 `data/report_context.json`。
3. 使用已登记的 `snapshot.quote`、`snapshot.news`、`snapshot.indicators`、`artifact.report_context`、`artifact.tracklist`、适用的 `artifact.position`、`artifact.research_summary`、`artifact.financial_collection_status` 和 `artifact.strategy_scan`。
4. 对每只持仓和核心观察股核验当日公告与新闻，保留来源链接和发布日期；优先交易所和公司公告。
5. 定量陈述只能来自 `market_breadth`、`multi-timeframe`、`relative_strength`、ATR/ADX/OBV/MFI/CMF、`strategy_stats`、`cross_market` 和 `portfolio_risk`。`unavailable`、`insufficient_data` 与 evidence gap 必须原样披露，不得补算或猜测。

## 深度研究复用

核心个股先读取 SQLite 最新 `research_summary` 与 `financial_collection_status`，只更新论点、证伪条件和预测事件的变化。重大业绩、监管、并购、核心假设变化或跨财报季度时先重跑 `$deep-stock-analysis`；普通价格波动不得每天重复整份深研。研究结论与交易决策必须分离。

## 单文件七章结构

写作前完整读取 `references/templates/daily-report-v2.md`，严格保留以下章节：

1. 宏观背景：四大指数、COMEX/SGE 金价、板块 TOP5 与市场宽度。
2. 持仓追踪：每只持仓成本、现价、盈亏、当日变化；A+H 双市场均覆盖。
3. 核心个股深度：工联、山金、三花、兆易、阿里逐只包含数据表、消息面、技术面、研究共振和操作判断；有 H 股的增加对比。若清单或数据变化，明确披露适用范围，不伪造数据。
4. A-H 对比：所有双市场股票的溢价和港股 PE。
5. 其余观察股巡检：覆盖清单中全部适用观察股，每只仅出现一次，并分为技术较强、中性震荡、技术偏弱；包含多周期趋势、ADX/RSI 强度证据、观察区、失效位、目标位和建议。
6. 策略信号：引用当日 `artifact.strategy_scan` 聚合结果，仅在变化时更新。
7. 操作清单：每只股票一句具体指令；actionable setup 必须包含 entry_zone、invalidation、targets、risk_reward，持仓操作具体到价格、股数和触发条件。

更新适用的 `position.json` 中 current price、unrealized pnl 与 loss 字段。不得用写单股报告代替七章中的深度分析。

## 完成与发布

1. 确认 `artifact.daily_report` 七章齐全、观察股全覆盖、来源有日期、缺失值未被猜测。
2. 提交并推送 Markdown 与适用的持仓更新。
3. 自动执行 `$deploy {date}`，由发布工作流生成 HTML、更新索引并推送。
4. 验证 GitHub Pages 上对应 HTML 可访问；发布失败则重试或停止，不得声称完成。

完成门禁以 `spec/workflows/daily-report.yaml` 和 `references/generated/workflows.md` 为准。
