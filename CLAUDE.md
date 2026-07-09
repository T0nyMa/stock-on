# Stock-On: 股票分析与追踪系统

Python 负责数据抓取和技术指标计算，Claude 负责所有分析决策。

## 核心规则

1. **先读后写**：分析任何股票前，Read tracking/ 下已有报告和 position.json
2. **具体到价位和股数**：不说"反弹就减仓"，说"48.5-49.5 缩量 → 卖出 1000 股"
3. **数据先行**：分析前必须 `python src/fetch.py --code {code}` + `python src/indicators.py --code {code}`
4. **日报/周报自动发布**：日报和周报生成完成后，必须自动执行 `/deploy` 推送到 GitHub Pages，不需要用户提醒

## 意图路由

看到以下用户意图时，Read 对应文档并按步骤执行：

| 用户说 | 执行 |
|--------|------|
| "分析三花" / "今日002050" | Read `references/scenarios/core-position.md` |
| "分析兆易创新" / "603986怎么样" | Read `references/scenarios/key-observation.md` |
| "巡检" / "观察列表" / "watchlist" | Read `references/scenarios/daily-patrol.md` |
| "建仓分析 {code}" / "新股票" | Read `references/scenarios/first-time-setup.md` |
| "扫描策略 {code}" / "策略分析" | Read `references/scenarios/strategy-scan.md` |
| "日报" / "今日总结" / "daily" | **严格执行日报七章流程，见下方「日报标准流程」** |
| "周报" / "本周总结" / "weekly" | 调用 `/weekly-report` Skill |
| "发布" / "deploy" | 调用 `/deploy` Skill |
| "潜力股" / "发现股票" / "发现机会" / "discovery" | 调用 `/discovery` Skill |
| "筛选" / "热门板块" | 调用 `/screener` Skill |
| "板块扫描" / "板块排名" / "热点板块" | 调用 `/sector-scan` Skill |

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

---

## 日报标准流程（强制执行，不可跳过）

用户说"日报"时，严格按以下步骤，一步不能漏：

### Step 0: 数据拉取

```bash
source .venv/bin/activate && python scripts/fetch_all_daily.py
```

一条命令拉取全部数据：A股21只+港股4只+指数+金价+板块。之后 Read `data/daily_snapshot.json` 获取全量数据。

### Step 1: 消息面搜索（必须AnySearch）

对**每只持仓股和核心观察股**，搜索最新公告/新闻：

```bash
uv run ~/.claude/skills/easy_anysearch_skill/search.py "{股票名} {代码} 2026年7月 最新消息"
```

### Step 2-7: 写报告（单文件）

**输出**: `tracking/daily/positions/YYYY-MM-DD.md`（一份文件，不拆分）

**七章结构**:
1. **宏观背景** — 四大指数 + 金价(COMEX/SGE) + 板块TOP5
2. **持仓追踪** — 每只持仓：成本/现价/浮亏/今日变化，A+H双市场都要
3. **核心个股深度** — 工联/山金/三花/兆易/阿里，每只 = 数据表→消息面→技术面→共振分析→操作判断，有H股的加港股对比子章节
4. **A-H对比** — 表格对比所有双市场股票的溢价和港股PE
5. **其余观察股概览** — 表格式：收盘/涨跌/PE/趋势/RSI
6. **策略信号** — 持仓股最新策略评分（有变化才更新）
7. **操作清单** — 每只一句话

### 完成检查清单

- [ ] Step 0 数据拉取完成（data/daily_snapshot.json 已生成）
- [ ] Step 1 消息面搜索完成（AnySearch，至少持仓股）
- [ ] 第一章：四大指数+金价+板块TOP5
- [ ] 第二章：持仓A+H双市场
- [ ] 第三章：四只A股深度+阿里巴巴，含H股对比
- [ ] 第四章：A-H全面对比表
- [ ] 第五章：其余观察股表
- [ ] 第七章：每只操作建议
- [ ] position.json 已更新浮亏
- [ ] git commit + push
