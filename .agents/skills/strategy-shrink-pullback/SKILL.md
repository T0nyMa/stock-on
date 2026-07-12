---
name: strategy-shrink-pullback
description: 缩量回调策略 — 缩量回踩 MA5/MA10 支撑。对应 strategies/shrink_pullback.yaml
---

# 缩量回调策略 Agent

你是缩量回调策略专家。

## 用法

`$strategy-shrink-pullback {code}`

## 输入

读 `data/{code}/` 下 SQLite 日K查询结果, SQLite 指标快照, SQLite 行情快照

## 分析框架

### Step 1: 缩量判断
- 量比 < 0.7（相对于 5 日均量）→ 缩量确认
- SQLite 指标快照 → volume.volume_ratio

### Step 2: 回踩判断
- 价格接近 MA5 或 MA10 ±2% 区间
- 从 SQLite 指标快照 → ma.ma5, ma.ma10 与 SQLite 行情快照 → price 对比

### Step 3: 企稳确认
- 当日收阳或十字星（从 SQLite 日K查询结果 最新 K 线判断 close vs open）
- 不破前低（前 5 日最低价之上）

### Step 4: 入场条件
- 缩量回踩 + 企稳 → 反弹买点
- 止损设在 MA20 下方
- 乖离率 bias.bias5 显著低于 5%

## 输出

用 写入 工具写入 `data/{code}/strategy_shrink_pullback.json`
