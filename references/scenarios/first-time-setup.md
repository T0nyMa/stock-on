# 场景：首次建仓分析

## 触发

"建仓分析 {code}" / "新股票 {code}" / "分析一下 {code} 能不能买"

## 适用

tracking/tracklist.json 中不存在的股票，或用户指定要新增追踪的股票

## 前置知识

references/analysis-methodology.md（完整四阶段）

## 步骤

### 1. 基本信息

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
source .venv/bin/activate && python src/indicators.py --code {code}
```

读取 SQLite 行情快照（运行 `python -m src.data_access --code {code} --kind quote`） → 价格、PE、PB、市值、换手率
读取 SQLite 基本面快照（运行 `python -m src.data_access --code {code} --kind fundamentals`） → 营收、利润、行业
读取 SQLite 日K（运行 `python -m src.data_access --code {code} --kind bars`） → 近60日走势概览

### 2. 归因分析（方法论 Phase 1）

- 近1月/3月涨跌幅 vs 大盘 vs 板块
- 找2-3只同行对比（同行业、相近市值）
- 结论：这只股票在行业中处于什么位置（领涨/跟涨/补涨/弱势）

### 3. 估值锚定（方法论 Phase 2）

**拆业务** → **定PE** → **算四层锚**：

```
铁底：历史最低PE × 当前EPS = X元
合理：行业平均PE × 当前EPS = X元
当前：现价PE × 当前EPS = X元
乐观：概念兑现PE × 当前EPS = X元
```

写入 `tracking/{code}-{name}/technical-analysis-report.md` 第二章。

### 4. 多策略共识扫描（5-7 个，完整执行）

先确定市场状态：使用 `$market-regime {code}` 或 读取 SQLite 指标快照（运行 `python -m src.data_access --code {code} --kind indicators`） → `trend.status`。

读取 `references/skills-index.md` → "按市场状态选策略"表。从"优先策略"列选 5 个 + "可选"列补 2 个。

逐个完整执行（**写 strategy JSON**）：

1. 读取 `.agents/skills/strategy-{name}/SKILL.md` 获取完整分析框架
2. 读取对应数据文件，按框架逐步分析
3. 输出信号 + 评分（0-100）+ 详细分析
4. 写入 `data/{code}/strategy_{name}.json`（格式参考各策略 Skill 定义的输出格式）

构建共识矩阵：

```
策略          类型    信号  评分  关键依据
均线金叉      趋势    buy   72   MA5上穿MA10, 量能确认
放量突破      量价    hold  55   量能不足未确认
...
共识：X买 Y持 Z卖 → 偏多/中性/偏空
```

加权评分 = Σ(score × weight) / Σ(weight)（权重见 skills-index.md）

### 5. 关键价位识别

从 SQLite 日K查询结果 提取：

- 近20日高/低点 → 短期箱体
- 近60日高/低点 → 中期区间
- MA20/MA60 → 均线支撑/阻力
- 斐波那契位（如适用）

### 6. 三情景构建

```
基准（概率50%）：区间震荡 → 下轨买、上轨卖
乐观（概率25%）：突破上行 → 突破上轨追入
悲观（概率25%）：破位下行 → 跌破支撑止损
```

每个情景：触发条件 + 操作指令 + 仓位变化。

### 7. 建立追踪

A) 将股票加入 `tracking/tracklist.json`

B) 创建追踪目录：
```
mkdir tracking/{code}-{name}/
```

C) 写入文件：
```
写入 tracking/{code}-{name}/technical-analysis-report.md  ← 完整报告（含策略共识矩阵）
写入 tracking/{code}-{name}/position.json                 ← 如已买入
```

D) 如已买入，写入持仓信息到 position.json

### 8. 报告模板

`technical-analysis-report.md` 首次创建时包含：

```
# {name}（{code}）技术分析报告

## 一、基本信息
（行业、市值、PE、PB、营收、利润）

## 二、基本面定位
（PE四层锚：铁底/合理/当前/乐观）

## 三、技术面
### 市场状态：{regime}
### 多策略共识矩阵
| 策略 | 类型 | 信号 | 评分 | 依据 |
### 趋势判断
### 关键价位表

## 四、情景分析
（三情景 + 概率 + 操作计划）

## 五、买入方案（如计划买入）
（目标区间、分批策略、止损位、仓位上限）
```

## 完成标志

- [ ] 市场状态已确定，5-7 个匹配策略已完整执行（JSON 已写入 data/）
- [ ] 共识矩阵已构建
- [ ] 完整报告已写入 tracking/{code}-{name}/
- [ ] 已加入 tracking/tracklist.json
- [ ] 买入方案（如有）具体到价位、仓位、止损
