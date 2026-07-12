---
name: market-regime
description: 从登记的 SQLite 指标快照判断市场状态并为当前工作流推荐策略
---

# market-regime

## 用法与输入

`$market-regime {code}`；先执行 `$tech-indicators {code}`。

只消费已登记的 `snapshot.indicators`：

```bash
python -m src.data_access --code {code} --kind indicators
```

缺失字段按 `DATA.QUALITY` 返回 `unavailable`，不得从未登记 sidecar 降级。

## 分类

- `trending_up`：MA5 > MA10 > MA20，MACD 零轴上方或金叉，价格在布林中轨上方。
- `volatile`：均线缠绕，价格在布林区间反复，MACD 零轴附近交叉。
- `sector_hot`：当前板块证据显示联动，个股量价与板块共振。
- `bearish`：MA5 < MA10 < MA20，价格在布林中轨下方。

返回 `regime`、`confidence`、`reasoning` 和 `recommended_strategies` 给调用中的 `quant-analysis`、`strategy-analysis` 或 research mode 使用。该返回值是工作流内的分类结果，不写入旁路文件；持久化技术事实仍由 `snapshot.indicators` 和 `artifact.report_context` 承担。

research mode 中仅解释技术环境与不确定性，不得升级为企业质量判断或交易动作；后续策略使用 `$strategy-executor ... mode=research`。
