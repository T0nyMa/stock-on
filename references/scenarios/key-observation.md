# 场景：重点观察股分析

## 触发

"分析兆易创新" / "603986怎么样" / "重点观察"

## 适用股票

tracking/tracklist.json 中 tier = "key"

## 前置知识

references/analysis-methodology.md（侧重 Phase 3 技术面）

## 步骤

### 1. 加载背景

```
读取 tracking/{code}-{name}/technical-analysis-report.md
读取 tracking/{code}-{name}/position.json         ← 可能只有买入计划，无实际持仓
```

记住：关键价位（支撑/阻力/目标入场区间）、买入条件、历史分析结论

### 2. 更新数据

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
source .venv/bin/activate && python src/indicators.py --code {code}
```

### 3. 策略扫描（2-3 个）

先确定市场状态：读取 SQLite 指标快照（运行 `python -m src.data_access --code {code} --kind indicators`） → `trend.status`

然后读取 `references/skills-index.md` → "按市场状态选策略"表。

从"优先策略"列选 2 个 + "可选"列补 1 个，聚焦：趋势类 + 量价类（最直接的技术信号）。

逐个执行（轻量，不写 JSON）：

1. 读取 `.agents/skills/strategy-{name}/SKILL.md` 获取分析框架
2. 读取对应数据文件，按框架判断
3. 记录：信号 + 评分 + 依据

### 4. 技术面快检

读取 SQLite 指标快照（运行 `python -m src.data_access --code {code} --kind indicators`）。在策略共识基础上补充细节：

| 指标 | 关注点 |
|------|--------|
| 趋势 | trend_strength 方向？均线排列变化？ |
| RSI | 超买(>70)还是健康(40-60)？ |
| MACD | HIST 放大/缩小？DIF方向？ |
| 量能 | 量比 > 1.2 放量？< 0.7 缩量？ |
| BIAS | 乖离率 > 5% 追高风险？ |

### 5. 买入条件检查

从 `technical-analysis-report.md` 中读取买入方案，逐项检查：

- 目标入场价区间是否到达？
- 回调是否缩量？（量比 < 0.7）
- 支撑位是否确认？（3日不破）
- 技术信号是否共振？（策略扫描 ≥ 2 个看多）

### 6. 板块联动

对比同板块其他观察股当日表现：
- 板块整体方向？（齐涨/齐跌/分化）
- 个股相对板块是领涨还是补涨？

### 7. 操作判断

根据买入条件检查结果：

- **触发买入条件** → 写买入建议，具体到价位和仓位
- **靠近但未触发** → 更新提醒价位，估算还需多久
- **条件恶化** → 提高入场门槛或移入观望
- **已持有观察仓** → 按核心持仓场景处理

### 8. 输出

```
写入 tracking/{code}-{name}/YYYY-MM-DD-analysis.md     ← 当日日报（异动时写）
写入 tracking/{code}-{name}/technical-analysis-report.md ← 更新技术面（含策略共识）和买入条件
```

平盘无重大变化时，不写日报，只更新 `technical-analysis-report.md` 中的关键数据（价格、日期、策略信号）。

## 完成标志

- [ ] 2-3 个优先策略已执行（轻量，结果写入报告）
- [ ] 关键价位和买入条件已检查
- [ ] technical-analysis-report.md 数据已刷新（含策略信号）
- [ ] 若触发买入信号，已具体写明操作建议
