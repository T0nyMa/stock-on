# 参考知识索引

分析时的按需参考层。`AGENTS.md` 路由到场景文档，场景文档引用本章节。

## 结构

```
references/
  README.md                       ← 本文件
  analysis-methodology.md         ← 完整四阶段方法论（Phase 1-4）
  screening-methodology.md        ← 三层筛选方法论（L1快照→L2指标→L3策略）
  skills-index.md                 ← 19个Skill用途 + 分类 + 参数
  gap-analysis.md                 ← 功能差距分析（开发阶段遗留）
  templates/
    daily-report-v2.md            ← 日报七章固定模板
  scenarios/                      ← 场景执行文档
    core-position.md              ← 核心持仓每日深度分析
    key-observation.md            ← 重点观察股分析
    daily-patrol.md               ← 每日批量巡检
    first-time-setup.md           ← 首次建仓分析
    strategy-scan.md              ← 多策略共识扫描
```

## 加载层级

```
Layer 1: AGENTS.md              → 常驻（路由）
Layer 2: scenarios/*.md         → 按用户意图加载（执行步骤）
Layer 3: analysis-methodology.md → 深度分析时加载（知识框架）
         skills-index.md         → 使用Skill时加载（工具参考）
```

## 何时读哪个

| 情况 | 读 |
|------|-----|
| 不知道怎么分析 | analysis-methodology.md |
| 不知道该用哪个Skill | skills-index.md |
| 场景步骤不清楚 | 对应 scenarios/*.md |
| 想看功能还缺什么 | gap-analysis.md |
| 生成日报 | templates/daily-report-v2.md |
