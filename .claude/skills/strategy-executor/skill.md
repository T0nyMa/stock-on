---
name: strategy-executor
description: 标准化策略执行器 — 读取策略定义，逐步执行，输出信号+评分+依据
---

# 策略执行器

标准化执行单个策略。被 daily-report 等场景调用，确保每次策略分析都走完整流程。

## 用法

`/strategy-executor {code} strategy-{name}`

例如：`/strategy-executor 002050 strategy-wave-theory`

## 流程

### Step 1: 加载策略定义

```
Read .claude/skills/strategy-{name}/skill.md
```

获取该策略的分析框架（Step 1/2/3/4）。

### Step 2: 读取数据

根据策略定义的"输入"章节，Read 对应数据文件：

```
data/{code}/kline.json
data/{code}/indicators.json
data/{code}/quote.json
data/{code}/news.json        ← 如策略需要
data/{code}/fundamentals.json ← 如策略需要
```

### Step 3: 逐步执行

严格按照策略定义中的 Step 1 → Step 2 → Step 3 → Step 4 执行。

每个 Step 必须引用具体数据，不能模糊：
- ✅ "量比 1.26 > 1.2 → 放量确认"
- ❌ "量能看起来还行"

### Step 4: 输出

输出必须包含三项，不省略：

```
信号: buy | hold | sell
评分: 0-100
依据: 一句话总结关键判据
```

示例输出：
```markdown
## strategy-wave-theory: buy (68)
C浪末端确认，44.11接近A浪低点44.5，78.6%回撤位守住
```

## 多策略并行

当需要执行多个策略时，可用 Agent 工具 spawn 并行执行（设置 run_in_background: true）：

```
Agent: /strategy-executor {code} strategy-wave-theory
Agent: /strategy-executor {code} strategy-emotion-cycle
Agent: /strategy-executor {code} strategy-bottom-volume
```

每个 Agent 独立返回信号+评分+依据，主进程汇总为共识矩阵。
