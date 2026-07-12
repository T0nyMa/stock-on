# 场景：核心持仓深度分析

## 研究底稿复用

读取 SQLite 最新 `research_summary`，逐项检查 thesis 与 falsification 是否变化。普通价格波动只引用研究底稿；重大业绩/监管/并购/核心假设变化或跨财报季度时，先重跑 `$deep-stock-analysis`，再进行持仓时机与仓位判断。

## 触发

"分析三花" / "今日002050" / "三花智控" / "看下持仓"

## 适用股票

tracking/tracklist.json 中 tier = "core" 且 has_position = true

## 前置知识

references/analysis-methodology.md（Phase 1-4 四阶段框架）

## 步骤

### 1. 加载背景

```
读取 tracking/{code}-{name}/technical-analysis-report.md
读取 tracking/{code}-{name}/position.json
```

必须记住：成本、股数、止损线、支撑位、阻力位、当前情景概率

### 2. 更新数据

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
source .venv/bin/activate && python src/indicators.py --code {code}
```

### 3. 策略扫描

先确定市场状态：读取 SQLite 指标快照（运行 `python -m src.data_access --code {code} --kind indicators`） → `trend.status`

然后读取 `references/skills-index.md` 的市场状态映射，选择足以覆盖主要证据维度的策略。

通过 `$strategy-executor` 执行 `strategy-analysis` 工作流：

1. 读取 `.agents/skills/strategy-{name}/SKILL.md` 获取分析框架
2. 读取对应数据文件，按框架判断
3. 记录信号、评分、关键依据和失效条件，并聚合为 `artifact.strategy_scan`

将策略扫描结果写入日报"技术面"章节的共识矩阵。

### 4. 归因（方法论 Phase 1）

读取 SQLite 行情快照（运行 `python -m src.data_access --code {code} --kind quote`），获取涨跌幅。

对比三个层级：
- 大盘：上证/深证/创业板当日涨跌
- 板块：所属行业指数涨跌
- 同行：2-3只同类个股涨跌

判断公式：个股涨跌 ≈ 大盘β + 板块α + 个股特异性。谁主因？

### 5. 估值检查（方法论 Phase 2）

读取 technical-analysis-report.md 第二章。

只检查变化，不重复计算：
- PE锚定是否失效？（股价大幅变动导致PE偏离）
- 有新财报/公告吗？
- 业务结构有变化吗？

无明显变化 → 沿用现有PE锚。

### 6. 技术面细节（补充策略扫描）

读取 SQLite 指标快照（运行 `python -m src.data_access --code {code} --kind indicators`）。在策略扫描共识基础上，补充细节：

| 指标 | 来源 | 对比项 |
|------|------|--------|
| 均线 | indicators.ma | MA5/10/20/60 排列 vs 昨日？价格站上哪条？ |
| MACD | indicators.macd | DIF/DEA 方向？HIST 放大/缩小？ |
| RSI | indicators.rsi | RSI6/12/24 vs 昨日？超卖(<30)/超买(>70)？ |
| 量能 | indicators.volume | 量比 vs 昨日？换手率？ |
| 趋势 | indicators.trend | trend_strength 和 status 变化？ |
| BIAS | indicators.bias | 乖离率修复还是恶化？ |

### 7. 关键价位评估

逐项核对 `position.json` 的 key_levels：

- [ ] 止损线：当日最低价 < stop_loss → **触发止损**
- [ ] 支撑位：当日最低价 > support → 支撑有效；盘中击穿但收回 → 警报
- [ ] 阻力位：收盘价 > resistance → 阻力突破，升级情景
- [ ] 成本线：距成本还有多远？回本需要多大涨幅？

### 8. 情景更新

从 `position.json` 读 `swing_plan`，逐情景判断：

- 基准情景（横盘磨底）：触发条件靠近了吗？概率 ±？
- 乐观情景（延续反弹）：触发条件靠近了吗？概率 ±？
- 悲观情景（再次下跌）：触发条件靠近了吗？概率 ±？

概率变化 > 10% 需说明原因。

### 9. 操作判断

必须具体到价位和股数：

- **减仓** → 若 A 条件触发：卖出 X 股 @ Y 元，剩余 Z 股，有效成本降至 C 元
- **持有** → 不操作。下次检查：N 日均线能否站稳
- **加仓** → 若 B 条件触发：买入 X 股 @ Y 元，总仓位 Z 股
- **止损** → 若 C 条件触发：全仓卖出 @ stop_loss，原因

### 10. 输出

```
写入 tracking/{code}-{name}/YYYY-MM-DD-analysis.md     ← 当日日报
写入 tracking/{code}-{name}/position.json               ← 更新 current_price, pnl, today_note, swing_plan
写入 tracking/{code}-{name}/technical-analysis-report.md ← 更新变化章节（行情、技术面（含策略共识）、情景概率）
```

## 日报格式

```markdown
# {name}（{code}）每日分析 — YYYY年MM月DD日

## 今日走势
| 开盘 | 最高 | 最低 | 收盘 | 涨跌 | 量比 | 换手 |

## 策略共识
| 策略 | 类型 | 信号 | 评分 | 依据 |
|------|------|------|------|------|

## 与昨日对比
| 指标 | 昨日 | 今日 | 方向 | 解读 |

## 关键价位评估
- [ ] 止损线 (Y元) — 是否触及
- [ ] 支撑位 (Y元) — 是否守住
- [ ] 阻力位 (Y元) — 是否突破

## 情景判断
| 情景 | 概率 | 变化 | 依据 |

## 操作建议
**操作：[减仓/持有/加仓/止损]**

1. 理由
2. 具体指令（如有）
3. 下次关注点

---
*分析时间：YYYY-MM-DD HH:MM*
*关键变化：一句话总结*
```

## 完成标志

- [ ] 匹配策略已通过 `strategy-analysis` 执行，结果引用 `artifact.strategy_scan`
- [ ] 日报已写入 tracking/
- [ ] position.json 已更新
- [ ] technical-analysis-report.md 关键数据已刷新（含策略共识矩阵）
- [ ] 操作建议具体到价位和股数
