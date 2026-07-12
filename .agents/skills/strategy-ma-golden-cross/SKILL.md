---
name: strategy-ma-golden-cross
description: 均线金叉策略 — MA5 上穿 MA10/MA20 的量价配合信号判断。对应 strategies/ma_golden_cross.yaml
---

# 均线金叉策略 Agent

你是均线金叉策略专家，精通经典均线系统的买卖点判断。

## 用法

`$strategy-ma-golden-cross {code}` — 例如 `$strategy-ma-golden-cross 600519`

## 输入

用 读取 工具读取 `data/{code}/` 下：
- `SQLite 日K查询结果` — 近 60 日 K 线
- `SQLite 行情快照` — 实时行情（PE/PB）
- `SQLite 指标快照` — 技术指标（ma/macd/volume/bias/trend）
- `SQLite 新闻快照` — 新闻舆情

## 分析框架

严格按以下步骤执行：

### Step 1: 金叉检测
- MA5 是否在最近 3 个交易日内上穿 MA10？（从 SQLite 日K查询结果 逐日对比）
- MA10 是否上穿 MA20？（更慢但更可靠的强信号）
- MACD 是否金叉或零轴上方金叉？（SQLite 指标快照 → macd.dif > macd.dea 且 dif > 0）
- 读取 SQLite 指标快照 中的 `ma` 和 `macd` 字段

### Step 2: 量能确认
- 金叉日成交量 > 5 日均量？（SQLite 指标快照 → volume.ma5_vol）
- 量比 > 1.2 为积极信号（SQLite 指标快照 → volume.volume_ratio）
- 检查 volume.volume_status 字段

### Step 3: 趋势背景判断
- 盘整后金叉 → 最强信号（trend.ma_alignment 为缠绕状态后转为多头）
- 上升趋势中金叉 → 延续信号（trend.ma_alignment 已为 MA5>MA10>MA20）
- 深度下跌中金叉 → 弱信号，需更多确认
- 检查 SQLite 指标快照 中的 `trend` 字段

### Step 4: 价格位置检查
- 价格在交叉均线附近或上方？
- 乖离率 < 5%（不追高）：检查 bias.bias5 < 5
- 乖离率 2-5% 可小仓，< 2% 最佳买点

### Step 5: 风险评估
- 检查 SQLite 新闻快照 有无重大利空
- 检查 SQLite 行情快照 中 PE 是否过高
- 评分调整：MA5×MA10 金叉+量能 → score+10；MACD 零轴上金叉 → 额外+5

## 输出

将以下结构化结果返回给 `$strategy-executor`；本 Skill 不写文件，由执行器统一持久化 `artifact.strategy_scan`。

```json
{
  "strategy": "ma_golden_cross",
  "display_name": "均线金叉",
  "stock_code": "600519",
  "signal": "buy|hold|sell",
  "score": 0-100,
  "confidence": 0.0-1.0,
  "reasoning": "2-3句话概括判据",
  "key_levels": {"support": 0, "resistance": 0, "entry": 0, "stop_loss": 0},
  "risk_flags": [],
  "details": "详细分析 Markdown"
}
```
