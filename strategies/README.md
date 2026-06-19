# strategies/ — 策略定义层

15 个自然语言交易策略，YAML 格式。策略定义分析框架，Claude Agent 按框架执行分析。

## 策略清单

| 文件 | 策略名称 | 类型 | 适用市场 |
|------|---------|------|---------|
| `ma_golden_cross.yaml` | 均线金叉 | 趋势 | 多头/反转 |
| `bull_trend.yaml` | 多头趋势 | 趋势 | 多头 |
| `volume_breakout.yaml` | 放量突破 | 量价 | 多头/震荡 |
| `shrink_pullback.yaml` | 缩量回调 | 量价 | 多头回调/空头 |
| `bottom_volume.yaml` | 地量 | 量价 | 空头末端 |
| `chan_theory.yaml` | 缠论 | 形态 | 震荡/空头末端 |
| `box_oscillation.yaml` | 箱体震荡 | 形态 | 震荡 |
| `wave_theory.yaml` | 波浪理论 | 形态 | 震荡/空头 |
| `hot_theme.yaml` | 热点题材 | 题材 | 题材驱动 |
| `event_driven.yaml` | 事件驱动 | 题材 | 事件驱动 |
| `emotion_cycle.yaml` | 情绪周期 | 题材 | 全部 |
| `growth_quality.yaml` | 成长质量 | 基本面 | 全部 |
| `expectation_repricing.yaml` | 预期重估 | 基本面 | 空头/震荡 |
| `dragon_head.yaml` | 龙头股 | 其他 | 题材驱动 |
| `one_yang_three_yin.yaml` | 一阳三阴 | 其他 | 多头回调 |

## 策略与 Skill 的关系

每个 YAML 策略对应 `.claude/skills/strategy-xxx/` 下的一个 Skill。Skill 是策略的执行载体，YAML 是策略的定义。

策略调用方式：`/strategy-{name} {code}`

## 策略选择原则

详见 references/skills-index.md 中的"按市场状态选策略"表。
