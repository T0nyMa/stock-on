---
name: discovery
description: 潜力股发现 — L1 快照、L2 评分、L3 策略验证与证据门槛筛选
---

# 潜力股发现

## Project contract

- Workflow: `discovery`
- Policies: `DATA.QUALITY`, `RESEARCH.EVIDENCE`
- Consumes: `snapshot.indicators`, `artifact.strategy_scan`
- Produces: `artifact.discovery_report`

执行 `discovery` 工作流，并使用 `references/scenarios/discovery.md` 的三层判断框架。

## 数据准备

```bash
source .venv/bin/activate && python src/screener.py
source .venv/bin/activate && python src/screener.py --l2
source .venv/bin/activate && python src/sector_scan.py
```

输入必须是当日登记的 `snapshot.indicators` 及可用扫描证据。缺失关键指标的股票排除，不以补零方式保留。

## L3 候选门槛

候选按证据规则进入 L3，而不是凑固定池规模：

- L2 ≥ 70：满足基础技术评分门槛。
- L2 ≥ 55 且位于当前强势板块：满足板块共振门槛。
- L2 55–69、涨幅 < 8%、成交额 > 100 亿元：可按流动性、风险和证据完整度择优。

去重并排除证据过期、重大事实未核验或关键字段 unavailable 的候选。候选数量由当日证据决定，允许为空。

## L3 策略验证

对每只候选读取 `snapshot.indicators` 判断市场状态，并通过 `$strategy-executor` 选择足以覆盖主要证据维度的策略。单策略 Skill 只返回内存结果；执行器统一形成并持久化 `artifact.strategy_scan`，其中包含归一化 buy/hold/sell 比例、weighted_score、证据和失效条件。

任务允许时可并行验证不同股票，但不得因并行便利改变评分门槛。

## 最终评分与推荐

```
综合分 = L2评分 × 0.4 + 策略加权评分 × 0.4 + 板块强度归一化 × 0.2
```

只有综合分达到评分门槛、关键事实有来源、风险与证伪条件完整的候选才可推荐。推荐还必须受当前 `artifact.tracklist` 的追踪容量约束：容量不足时保留最高证据强度者，其余进入候补；没有合格候选时输出空推荐，不降低门槛。

最终写入登记的 `artifact.discovery_report`。仅在用户授权且追踪容量允许时更新 `artifact.tracklist`，新增项使用 `tier: watch`。

## 完成标志

- L1、L2 与板块证据为当前数据。
- L3 候选全部通过明确证据门槛，策略验证引用 `artifact.strategy_scan`。
- 推荐满足评分门槛、来源与证伪要求，并遵守追踪容量。
- 报告已写入 `artifact.discovery_report`；状态变更仅在授权时写入 `artifact.tracklist`。
