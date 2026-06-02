---
name: tech-indicators
description: 计算股票技术指标，写入 data/{code}/indicators.json。Phase 1 数据准备第二步。
---

# tech-indicators

基于 K 线数据计算技术指标。

## 用法

`/tech-indicators {code}` — 例如 `/tech-indicators 600519`

前置条件：`/fetch-data {code}` 必须先执行。

## 执行

```bash
source .venv/bin/activate && python src/indicators.py --code {code}
```

## 输出

写入 `data/{code}/indicators.json`，包含：

| 指标组 | 字段 |
|--------|------|
| 均线系统 | ma5, ma10, ma20, ma60 |
| MACD | dif, dea, hist |
| RSI | rsi6, rsi12, rsi24 |
| 量能 | ma5_vol, volume_ratio, volume_status |
| 乖离率 | bias5, bias10, bias20 |
| 趋势判断 | status, ma_alignment, support_levels, resistance_levels |
| 买入信号 | signal, score, reasons |
| 风险因子 | risk_factors |

## 验证

确认 `data/{code}/indicators.json` 存在。
