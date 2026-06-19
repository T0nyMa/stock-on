---
name: daily-report
description: 每日追踪报告 — 生成大盘总结 + 全部追踪股单股日报 + 持仓汇总
---

# 每日追踪报告

编排每日报告生成流程。严格按步骤执行，不跳过。

## 用法

`/daily-report` 或用户说"日报""今日总结""daily"

## 流程

### Phase 1: 数据准备

```bash
# 大盘指数
source .venv/bin/activate && python src/fetch_market.py

# 追踪股数据（读取 tracklist.json 后并行执行）
Read tracking/tracklist.json → 取全部 stocks[].code
对每只 stock.code 并行执行:
  bash: source .venv/bin/activate && python src/fetch.py --code {code}
  bash: source .venv/bin/activate && python src/indicators.py --code {code}
```

### Phase 2: 单股日报（全部股票，每只必写）

Read `tracking/tracklist.json`，按 tier 决定分析深度。每只股票生成一份单股日报。

**策略分析方法（内联，不调用外部 Skill）：**

```
1. Read data/{code}/indicators.json → 从 trend.status 确定市场状态
2. Read references/skills-index.md → "按市场状态选策略"表
3. 根据市场状态从"优先策略"列选对应数量:
   - core: 优先列选 3-4 + 可选列补 1 = 共 3-5 个
   - key:  优先列选 2-3 = 共 2-3 个
   - watch: 优先列选 1-2 = 共 1-2 个
4. 对每个选中的策略，读取其 Skill 定义（.claude/skills/strategy-{name}/skill.md）
5. 按 Skill 定义的 Step 1→2→3→4 逐步执行，引用具体数据
6. 每个策略输出: 信号(buy/hold/sell) + 评分(0-100) + 依据(一句话)
7. 汇总为策略共识矩阵
```

**日报格式（按 tier）：**

core — 完整日报（含策略共识矩阵）:
```markdown
# {name}（{code}）每日分析 — YYYY年MM月DD日

## 今日走势
| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |

## 策略共识 (3-5策略)
| 策略 | 类型 | 信号 | 评分 | 依据 |

## 与昨日对比
| 指标 | 昨日 | 今日 | 方向 | 解读 |

## 关键价位评估
（止损/支撑/阻力/成本，逐项检查）

## 情景判断
| 情景 | 概率 | 变化 | 依据 |

## 操作建议
具体到价位和股数
```

key — 标准日报（含策略信号）:
```markdown
# {name}（{code}）每日分析

## 今日走势

## 策略信号 (2-3策略)

## 指标变化

## 买入条件检查

## 操作建议
```

watch — 简化日报（含策略信号）:
```markdown
# {name}（{code}）每日分析

## 今日走势

## 策略信号 (1-2策略)

## 指标变化

## 操作建议
```

**输出文件：**
```
tracking/{code}-{name}/YYYY-MM-DD-analysis.md ← 每只必写
tracking/{code}-{name}/position.json           ← core 更新
tracking/{code}-{name}/technical-analysis-report.md ← 更新变化章节
```

**并行建议：**

7只股票的策略分析可以并行。用 Agent 工具 spawn 7 个 Agent（run_in_background: true），每只 Agent 独立完成：读数据 → 选策略 → 分析 → 写日报。这样 7 只同时完成，不阻塞。

### Phase 3: 大盘总结

Read `data/market/index.json` → 输出大盘日报。

格式：4大指数表现 + 今日特征（风格定性/量能/最强最弱指数）+ 与昨日对比。

Write `tracking/daily/market/YYYY-MM-DD.md`

### Phase 4: 持仓观察汇总

将 Phase 2 所有单股日报汇总为三层日报：

```
★ 核心持仓 — 每只 5-8 行（策略共识 + 关键价位 + 操作）
★ 重点观察 — 每只 3-5 行（策略信号 + 买入条件）
一般观察 — 表格式，一行一只（收盘/涨跌/量比/RSI/状态）
```

Write `tracking/daily/positions/YYYY-MM-DD.md`

## 输出清单（必须全部生成）

```
tracking/daily/market/YYYY-MM-DD.md              ← 大盘总结
tracking/daily/positions/YYYY-MM-DD.md           ← 持仓观察汇总
tracking/{code}-{name}/YYYY-MM-DD-analysis.md    ← 全部 N 只单股日报（以 tracklist.json 为准）
```

## 完成标志

- [ ] fetch_market.py 已执行
- [ ] 全部追踪股 fetch + indicators 已完成
- [ ] 大盘总结已写入
- [ ] 全部 N 只单股日报已写入（core: 3-5策略 / key: 2-3策略 / watch: 1-2策略）
- [ ] 持仓观察汇总日报已写入
