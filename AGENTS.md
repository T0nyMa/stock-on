# Stock-On: 股票分析与追踪系统

Python 负责确定性数据抓取与指标计算，Codex 负责基于已登记证据的研究和决策。`spec/` 是路由、工作流、Skill、工件和门禁的机器可读事实源。

## 不变量

1. 分析前先读取 `tracking/` 下已有报告、`tracking/tracklist.json` 和适用的 `position.json`。
2. 需要行情和技术指标时，先执行已登记的数据准备与量化工作流；缺失字段必须保留为 `unavailable`，不得猜测。
3. 时效性事实必须联网核验，优先交易所、公司公告及权威来源，并保留链接与日期。
4. 研究与交易决策分离；交易指令必须具体到价格、股数、触发条件和失效条件。
5. 日报和周报完成后必须执行发布工作流，并验证 commit、push 和发布结果。

## 优先级

用户明确要求 > `AGENTS.md` 手工不变量 > `spec/` 登记的工作流与门禁 > 场景说明和 Skill 实现细节。冲突时遵循更高优先级，并显式披露无法满足的低优先级要求。

## 意图路由

下表由 `spec/routes.yaml` 生成；不要手工编辑标记区域。

<!-- BEGIN GENERATED: routes -->
| Route ID | 用户意图 | Workflow | Skill | 优先级 |
|---|---|---|---|---:|
| `daily-report` | “日报”<br>“今日总结”<br>“daily” | `daily-report` | `$daily-report` | 70 |
| `deep-research` | “深度分析 {code}”<br>“深研 {code}” | `deep-research` | `$deep-stock-analysis` | 100 |
| `deploy` | “发布”<br>“deploy” | `deploy` | `$deploy` | 50 |
| `discovery` | “潜力股”<br>“发现股票”<br>“发现机会”<br>“discovery” | `discovery` | `$discovery` | 60 |
| `financial-report` | “财报分析 {code}”<br>“财报深度解析 {code}”<br>“财报排雷 {code}”<br>“财务质量 {code}” | `financial-report` | `$financial-report-analysis` | 100 |
| `position-decision` | “建仓分析 {code}”<br>“新股票 {code}”<br>“分析三花”<br>“今日002050”<br>“分析兆易创新”<br>“603986怎么样” | `position-decision` | `$decision-agent` | 90 |
| `screener` | “筛选”<br>“热门股” | `discovery` | `$screener` | 60 |
| `sector-scan` | “板块扫描”<br>“板块排名”<br>“热点板块” | `discovery` | `$sector-scan` | 60 |
| `strategy-analysis` | “扫描策略 {code}”<br>“策略分析 {code}” | `strategy-analysis` | `$strategy-executor` | 80 |
| `weekly-report` | “周报”<br>“本周总结”<br>“weekly” | `weekly-report` | `$weekly-report` | 70 |
<!-- END GENERATED: routes -->

## 目录导航

| 目录 | 说明 | 入口 |
|---|---|---|
| `spec/` | 项目注册表：路由、工作流、策略、工件、Skill | `spec/project.yaml` |
| `src/` | Python 数据层和 spec 引擎 | `src/README.md` |
| `strategies/` | 策略定义 | `strategies/README.md` |
| `tracking/` | 追踪报告、清单和持仓 | `tracking/README.md` |
| `references/` | 方法论、模板和生成索引 | `references/README.md` |
| `data/` | SQLite 数据和确定性派生工件 | `python -m src.data_access` |
| `.agents/skills/` | 项目 Skill 实现 | `references/skills-index.md` |

## 渐进式加载

先用本文件和生成路由定位 `spec/workflows/{workflow}.yaml`，再加载其中登记的 policies、artifacts 和 skills；仅在工作流需要时读取对应场景、方法论与模板。具体执行步骤和完成门禁以工作流注册项为准。
