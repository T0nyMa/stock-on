---
name: weekly-report
description: 每周总结 — 汇总本周日报生成周度视角
---

# 每周总结

## 深度研究复用

读取核心股票最新 `research_summary`，汇总本周 thesis、falsification 与 confidence 的变化。读取 `financial_collection_status`，汇总本周新增电话会、预估调整、监管/媒体信息及其正式验证事件；不得把第三方前瞻写成已实现业绩。只有重大业绩/监管/并购/核心假设变化或季度刷新才触发 `$deep-stock-analysis`，并保持周报完成后自动 `$deploy`。

汇总本周日报，生成周度视角的报告。

## Quantitative Analysis V2 周度要求

周报必须包含真实 `weekly` 指标、`breadth` 周内趋势、`relative-strength` 排名变化及 `prior-call` 复盘（上周 entry/invalidation/target 是否触发）。不得把每日指标串联冒充周线计算；缺失字段显示 `unavailable`。

## 用法

`$weekly-report` 或用户说"周报""本周总结""weekly"

## 前置

需本周至少有 1 份日报（tracking/daily/ 下有文件）

## 流程

### 1. 收集本周日报

```
ls tracking/daily/market/     → 取本周所有日期文件
ls tracking/daily/positions/  → 取本周所有日期文件
ls tracking/{code}-{name}/    → 取本周所有单股日报
```

### 2. 读取数据

- 读取 本周所有大盘日报
- 读取 本周所有持仓汇总日报
- 读取 `tracking/tracklist.json` → 获取当前追踪清单
- 读取 每只股票最新的 technical-analysis-report.md

### 3. 生成大盘周评

从本周大盘日报中提取每日指数数据，汇总：

```
- 4大指数周涨跌（周一 vs 周五）
- 周度特征：风格（成长/价值）、节奏（哪几天强哪几天弱）
- 与上周对比
```

### 4. 生成板块周评

从追踪股 tags 聚合板块表现：

```
- 按 tags 分组计算周涨幅均值
- 最强/最弱板块
- 板块轮动观察
```

### 5. 生成持仓周评

**core 股票**：周走势 + 趋势变化 + 关键事件 + 操作回顾 + 下周关注
**key 股票**：周走势简述 + 买入条件状态 + 下周关注
**watch 股票**：表格式，周涨跌 + 状态

### 6. 输出

写入 `tracking/weekly/YYYY-MM-DD.md`

### 7. 发布

周报生成后，**必须自动执行部署**：

使用 `$deploy {date}` — 生成周报 HTML + 更新首页 + git push

格式：
```markdown
# 周度总结 — YYYY年Wxx周（M月D日 - M月D日）

## 大盘周评
（指数表格 + 周度特征）

## 板块表现
（从追踪股反推）

## 持仓周评
### ★ 核心持仓
### ★ 重点观察
### 一般观察概览

## 下周关注
（关键事件/价位提醒/异动跟进）
```

## 完成标志

- [ ] 本周所有日报已收集
- [ ] 大盘周度表现已汇总
- [ ] 每只股票周评已更新
- [ ] 下周关注点已列出
- [ ] **已部署到 GitHub Pages**（HTML + index.html + git push）
