# Stock-On: 股票分析与追踪系统

Python 负责数据抓取和技术指标计算，Codex 负责所有分析决策。

## 核心规则

1. **先读后写**：分析任何股票前，先读取 `tracking/` 下已有报告和 `position.json`
2. **具体到价位和股数**：不说“反弹就减仓”，说“48.5-49.5 缩量 → 卖出 1000 股”
3. **数据先行**：分析前必须运行 `python src/fetch.py --code {code}` 和 `python src/indicators.py --code {code}`
4. **日报/周报自动发布**：日报和周报生成完成后，必须执行 `$deploy` 推送到 GitHub Pages，不需要用户提醒
5. **联网信息必须核验**：新闻、公告、行情等时效性信息必须联网搜索；优先交易所公告、公司公告及权威财经来源，并在报告中保留来源链接和日期

## 意图路由

看到以下用户意图时，读取对应文档或使用对应 Skill，并按步骤执行：

| 用户说 | 执行 |
|--------|------|
| “分析三花” / “今日002050” | 读取 `references/scenarios/core-position.md` |
| “分析兆易创新” / “603986怎么样” | 读取 `references/scenarios/key-observation.md` |
| “巡检” / “观察列表” / “watchlist” | 读取 `references/scenarios/daily-patrol.md` |
| “建仓分析 {code}” / “新股票” | 读取 `references/scenarios/first-time-setup.md` |
| “扫描策略 {code}” / “策略分析” | 读取 `references/scenarios/strategy-scan.md` |
| “日报” / “今日总结” / “daily” | 使用 `$daily-report`，严格执行日报七章流程 |
| “周报” / “本周总结” / “weekly” | 使用 `$weekly-report` |
| “发布” / “deploy” | 使用 `$deploy` |
| “潜力股” / “发现股票” / “发现机会” / “discovery” | 使用 `$discovery` |
| “筛选” / “热门股” | 使用 `$screener` |
| “板块扫描” / “板块排名” / “热点板块” | 使用 `$sector-scan` |

## 追踪清单

读取 `tracking/tracklist.json` 获取当前追踪的所有股票及其分层和场景。

## 目录导航

| 目录 | 说明 | 入口 |
|------|------|------|
| `src/` | Python 数据层 | `src/README.md` |
| `strategies/` | 策略定义 | `strategies/README.md` |
| `tracking/` | 追踪报告 + 追踪清单 | `tracking/README.md` |
| `references/` | 参考知识（方法论、场景、Skill 索引） | `references/README.md` |
| `data/` | 运行时 JSON 数据 | 直接读取对应文件 |
| `.agents/skills/` | Codex 项目 Skill 定义 | 按需使用 |

## 渐进式加载

```text
用户意图
  → AGENTS.md（本文件，常驻）→ 匹配路由
    → references/scenarios/{场景}.md（按需加载）→ 步骤执行
      → references/analysis-methodology.md（深度分析时加载）→ 知识框架
      → references/skills-index.md（使用 Skill 时加载）→ 工具参数
```

本文件只做路由；具体工作流以对应场景文档和 Skill 为准。

## 日报标准流程（强制执行，不可跳过）

用户说“日报”时，使用 `$daily-report`，并确保以下步骤完整执行。

### Step 0: 数据拉取

```bash
source .venv/bin/activate && python scripts/fetch_all_daily.py
```

该命令拉取 A 股、港股、指数、金价和板块数据。之后读取 `data/daily_snapshot.json` 获取全量数据。

### Step 1: 消息面搜索

对每只持仓股和核心观察股联网搜索最新公告与新闻。查询中使用执行当天的日期，不要硬编码月份；优先核验一手来源，并记录链接与发布日期。

### Step 2-7: 写报告（单文件）

写任何定量结论前必须读取 `data/report_context.json`。定量字段只允许来自 `market_breadth`、`multi-timeframe`、`relative_strength`、`strategy_stats`、`cross_market` 和 `portfolio_risk`。报告必须展示 ATR、entry、invalidation、targets 与 risk_reward；字段为 `unavailable` 时原样披露，不得自行补算或降级成中性判断。

输出：`tracking/daily/positions/YYYY-MM-DD.md`（一份文件，不拆分）

七章结构：

1. **宏观背景** — 四大指数 + 金价（COMEX/SGE）+ 板块 TOP5
2. **持仓追踪** — 每只持仓：成本/现价/浮亏/今日变化，A+H 双市场都要
3. **核心个股深度** — 工联/山金/三花/兆易/阿里，每只包含数据表、消息面、技术面、共振分析和操作判断；有 H 股的增加港股对比子章节
4. **A-H 对比** — 表格对比所有双市场股票的溢价和港股 PE
5. **其余观察股概览** — 表格式：收盘/涨跌/PE/趋势/RSI
6. **策略信号** — 持仓股最新策略评分（有变化才更新）
7. **操作清单** — 每只一句话

### 完成检查清单

- [ ] Step 0 数据拉取完成，`data/daily_snapshot.json` 已生成
- [ ] Step 1 消息面搜索完成，至少覆盖持仓股，并保留来源链接与日期
- [ ] 第一章包含四大指数、金价和板块 TOP5
- [ ] 第二章包含持仓 A+H 双市场
- [ ] 第三章包含四只 A 股深度分析和阿里巴巴，含 H 股对比
- [ ] 第四章包含 A-H 全面对比表
- [ ] 第五章包含其余观察股表
- [ ] 第七章包含每只股票的操作建议
- [ ] `position.json` 已更新浮亏
- [ ] 已完成 git commit 和 push
