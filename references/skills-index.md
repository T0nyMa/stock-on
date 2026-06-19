# Skills 索引

全部 Skill 的用途、分类和参数。

## 编排类（新增）

| Skill | 说明 |
|-------|------|
| `daily-report` | 每日追踪报告编排：大盘 + 7只单股日报（按tier执行不同策略数） + 持仓汇总 |
| `weekly-report` | 周度总结：汇总本周日报生成周报 |
| `strategy-executor {code} {strategy}` | 标准化策略执行器：读策略定义 → 逐步执行 → 输出信号+评分+依据 |
| `deploy {date}` | 发布到 GitHub Pages：生成HTML + 更新首页索引 + git push |

## 数据准备

| Skill | 别名 | 说明 |
|-------|------|------|
| `fetch-data {code}` | `python src/fetch.py --code {code}` | 拉取 K线+行情+基本面+新闻 |
| `tech-indicators {code}` | `python src/indicators.py --code {code}` | 计算 MA/MACD/RSI/量能/BIAS/趋势 |

## 市场状态

| Skill | 输入 | 输出 | 说明 |
|-------|------|------|------|
| `market-regime {code}` | indicators.json | regime.json | 判断市场状态，推荐匹配策略 |

## 策略分析（按类型）

### 趋势类（权重 1.0）

| Skill | 适用市场 | 核心判据 |
|-------|---------|---------|
| `strategy-ma-golden-cross {code}` | 多头/反转 | MA金叉 + 量能确认 + 乖离率 |
| `strategy-bull-trend {code}` | 多头 | MA5>MA10>MA20 + MACD零轴上 + 回踩不破 |

### 量价类（权重 1.0）

| Skill | 适用市场 | 核心判据 |
|-------|---------|---------|
| `strategy-volume-breakout {code}` | 多头/震荡 | 放量突破阻力 + 收盘站上 + 不限高 |
| `strategy-shrink-pullback {code}` | 多头回调/空头 | 缩量回踩均线 + 企稳阳线 + 不破前低 |
| `strategy-bottom-volume {code}` | 空头末端 | 地量(量比<0.5) + RSI超卖 + 止跌企稳 |

### 形态类（权重 0.9）

| Skill | 适用市场 | 核心判据 |
|-------|---------|---------|
| `strategy-chan-theory {code}` | 震荡/空头末端 | 分型→笔→中枢→背驰→买卖点 |
| `strategy-box-oscillation {code}` | 震荡 | 20日箱体 + 下轨买/上轨卖 + 量能配合 |
| `strategy-wave-theory {code}` | 震荡/空头 | 推动浪/调整浪识别 + 斐波那契 + 浪规检查 |

### 题材类（权重 0.8）

| Skill | 适用市场 | 核心判据 |
|-------|---------|---------|
| `strategy-hot-theme {code}` | 题材驱动 | 热点识别 + 相关性 + 强度判断 + 节奏 |
| `strategy-event-driven {code}` | 事件驱动 | 事件冲击评估 + 持续性判断 + 时效 |
| `strategy-emotion-cycle {code}` | 全部 | 冰点/启动/高潮/退潮 + 换手率 + 涨跌停 |

### 基本面类（权重 0.7）

| Skill | 适用市场 | 核心判据 |
|-------|---------|---------|
| `strategy-growth-quality {code}` | 全部 | 营收/利润增速 + 估值分位 + 质量筛查 |
| `strategy-expectation-repricing {code}` | 空头/震荡 | 预期差识别 + 催化剂 + 重估空间 |

### 其他（权重 0.9）

| Skill | 适用市场 | 核心判据 |
|-------|---------|---------|
| `strategy-dragon-head {code}` | 题材驱动 | 相对强度 + 领涨属性 + 资金聚焦 |
| `strategy-one-yang-three-yin {code}` | 多头回调 | 一阳吞三阴 + 量能确认 + 支撑不破 |

## 决策汇总

| Skill | 输入 | 输出 | 说明 |
|-------|------|------|------|
| `decision-agent {code}` | 所有 strategy_*.json + regime.json | decision.json | 加权评分 + 风险汇总 + 操作建议 |

## 按市场状态选策略

| 市场状态 | 优先策略（前5） | 可选 |
|----------|----------------|------|
| trending_up（多头） | ma-golden-cross, volume-breakout, bull-trend, dragon-head, shrink-pullback | hot-theme, emotion-cycle |
| volatile（震荡） | chan-theory, box-oscillation, wave-theory, bottom-volume, one-yang-three-yin | ma-golden-cross, shrink-pullback |
| sector_hot（题材） | hot-theme, dragon-head, event-driven, emotion-cycle, volume-breakout | bull-trend |
| bearish（空头） | expectation-repricing, growth-quality, event-driven, bottom-volume, emotion-cycle | shrink-pullback |
