# Stock-On: 股票分析与追踪系统

Python 负责数据抓取和技术指标计算，Claude 负责所有分析决策。

## 核心规则

1. **先读后写**：分析任何股票前，Read tracking/ 下已有报告和 position.json
2. **具体到价位和股数**：不说"反弹就减仓"，说"48.5-49.5 缩量 → 卖出 1000 股"
3. **数据先行**：分析前必须 `python src/fetch.py --code {code}` + `python src/indicators.py --code {code}`

## 意图路由

看到以下用户意图时，Read 对应文档并按步骤执行：

| 用户说 | 执行 |
|--------|------|
| "分析三花" / "今日002050" | Read `references/scenarios/core-position.md` |
| "分析兆易创新" / "603986怎么样" | Read `references/scenarios/key-observation.md` |
| "巡检" / "观察列表" / "watchlist" | Read `references/scenarios/daily-patrol.md` |
| "建仓分析 {code}" / "新股票" | Read `references/scenarios/first-time-setup.md` |
| "扫描策略 {code}" / "策略分析" | Read `references/scenarios/strategy-scan.md` |
| "日报" / "今日总结" / "daily" | 调用 `/daily-report` Skill |
| "周报" / "本周总结" / "weekly" | 调用 `/weekly-report` Skill |
| "发布" / "deploy" | 调用 `/deploy` Skill |

## 追踪清单

Read `tracking/tracklist.json` 获取当前追踪的所有股票及其分层和场景。

## 目录导航

遇到需要了解各目录职责时：

| 目录 | 说明 | 入口 |
|------|------|------|
| `src/` | Python 数据层 | Read `src/README.md` |
| `strategies/` | 15个策略定义 | Read `strategies/README.md` |
| `tracking/` | 追踪报告 + 追踪清单 | Read `tracking/README.md` |
| `references/` | 参考知识（方法论、场景、Skill索引） | Read `references/README.md` |
| `data/` | 运行时JSON数据 | 直接 Read 对应文件 |
| `.claude/skills/` | Skill 定义 | 按需调用 |

## 渐进式加载

```
用户意图
  → CLAUDE.md（本文件，常驻）→ 匹配路由
    → references/scenarios/{场景}.md（按需加载）→ 步骤执行
      → references/analysis-methodology.md（深度分析时加载）→ 知识框架
      → references/skills-index.md（使用Skill时加载）→ 工具参数
```

本文件只做路由，不包含具体分析步骤。
