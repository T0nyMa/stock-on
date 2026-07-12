---
name: weekly-report
description: 从登记的单文件日报和当前摘要生成周度报告并发布
---

# 每周总结

执行 `weekly-report` 工作流。唯一日报来源是本周登记的 `artifact.daily_report`：

`tracking/daily/positions/YYYY-MM-DD.md`

不得读取拆分的大盘目录或逐股日报。当前股票清单、持仓、量化与研究信息分别使用 `artifact.tracklist`、`artifact.position`、`artifact.report_context`、`snapshot.indicators`、`artifact.research_summary` 和 `artifact.financial_collection_status`。

## 前置

本周至少存在一份已登记日报。逐日读取其七章内容，日期必须落在目标周内；缺失交易日明确披露，不用其他非登记文件补齐。

## 周度要求

- 使用真实 `weekly` 指标，不得把日指标串联冒充周线计算。
- 汇总 `breadth` 周内趋势、relative-strength 排名变化，以及上周 entry/invalidation/target 的 prior-call 复盘。
- 汇总指数、板块、持仓、核心研究论点、策略与组合风险的周内变化，并保留证据日期。
- `unavailable` 原样显示；第三方预测不得写成已实现业绩。

核心股票复用最新 `research_summary` 与 `financial_collection_status`。只有重大业绩、监管、并购、核心假设变化或季度刷新才触发 `$deep-stock-analysis`。

## 输出结构

写入登记的 `artifact.weekly_report`，至少包含：大盘周评、板块表现、持仓与观察股周评、本周论点/策略/风险变化、prior-call 复盘和下周关注。操作判断具体到价位、触发条件和失效条件。

生成后自动执行 `$deploy {date}`，提交、推送并验证发布 HTML。完成门禁以 `spec/workflows/weekly-report.yaml` 为准。
