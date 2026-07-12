---
name: market-regime
description: 读取技术指标，判断市场状态，推荐分析策略。Phase 2。
---

# market-regime

市场状态识别 Agent。根据技术指标判断当前市场处于什么状态，推荐最匹配的分析策略。

## 用法

`$market-regime {code}` — 例如 `$market-regime 600519`

前置条件：`$tech-indicators {code}` 必须先执行。

## 输入

读取 SQLite 指标快照（运行 `python -m src.data_access --code {code} --kind indicators`）

## 分析方法

依次检查以下市场状态：

### 1. trending_up（多头趋势）
- MA5 > MA10 > MA20 多头排列
- MACD 在零轴上方或金叉
- 价格在布林带中轨上方运行
- **匹配策略**：均线金叉、放量突破、多头趋势、缩量回调、龙头股

### 2. volatile（震荡盘整）
- 均线缠绕，无明显方向
- 价格在布林带上下轨之间反复
- MACD 在零轴附近反复交叉
- **匹配策略**：缠论、箱体震荡、波浪理论、地量、一阳三阴

### 3. sector_hot（热点题材）
- 板块联动明显，个股与板块共振
- 成交量放大
- **匹配策略**：热点题材、事件驱动、情绪周期、龙头股

### 4. bearish（空头趋势）
- MA5 < MA10 < MA20 空头排列
- 价格在布林带中轨下方运行
- **匹配策略**：预期重估、成长质量、事件驱动

## 输出

用 写入 工具写入 `data/{code}/regime.json`：

```json
{
  "regime": "trending_up|volatile|sector_hot|bearish",
  "confidence": 0.85,
  "reasoning": "MA5>MA10>MA20 多头排列，MACD 零轴上方运行，价格沿MA5上行",
  "recommended_strategies": [
    {"name": "ma_golden_cross", "priority": 20, "reason": "多头趋势下金叉信号可靠"},
    {"name": "volume_breakout", "priority": 30, "reason": "趋势向上时突破信号有效"},
    {"name": "bull_trend", "priority": 15, "reason": "当前处于强势多头"}
  ]
}
```
