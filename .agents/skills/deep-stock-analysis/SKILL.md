---
name: deep-stock-analysis
description: 对单只股票做研究级深度分析，融合公司类型、基本面、行业周期、竞争壁垒、治理、筹码、估值、量化技术与可证伪情景；用于“深度分析/深研某股票”，不负责建仓、持仓或交易时机决策。
---

# 股票深度分析

## Project contract

- workflow: deep-research
- consumes: `snapshot.fundamentals`, `snapshot.news`, `artifact.financial_collection_status`, `artifact.financial_quality_summary`
- produces: `artifact.research_summary`
- policies: `DATA.QUALITY`, `SEARCH.PRIORITY`, `RESEARCH.EVIDENCE`, `DECISION.SEPARATION`

产出可复用、可追溯、可证伪的公司研究底稿。研究结论是建仓分析、持仓决策、日报和周报的上游输入。

## 硬边界

- 不得输出买入、卖出、持有、加减仓、目标价、交易价位、股数或止损。
- 可以解释价格反映了什么预期、技术状态和潜在催化，但结论必须停在研究层。
- 时效性事实必须联网核验，保留来源链接和发布日期；公告、财报、交易所材料优先于媒体与自媒体。
- 事实、推断、假设分开表达；缺失证据写入 evidence gap，不得补造。

## 调用

`$deep-stock-analysis {code}`，也接受股票名称。先解析市场和标准代码，再执行全流程。

## 前置读取与能力复用

1. 读取 `tracking/tracklist.json`、匹配股票目录下已有报告，以及 `position.json`（仅理解关注背景，不推导交易动作）。
2. 读取 `references/analysis-methodology.md`、[核心框架](references/core-framework.md)和[集成契约](references/integration-contract.md)。
3. 按 AGENTS.md 先运行 `python src/fetch.py --code {code}` 和 `python src/indicators.py --code {code}`；读取 SQLite 的 bars、quote、fundamentals、news、indicators。
4. 用 Quantitative Analysis V2 读取 500 日、多周期、相对强弱、ATR/ADX/OBV/MFI/CMF；不得重复计算已有指标。
5. 通过 `$market-regime` 路由技术策略，并以 `$strategy-executor ... mode=research` 解释信号。
6. 当前公告、新闻、行业、商品、监管和股东信息使用 EasyAnySearch 搜索并核验。

## 公司类型路由

只能选择一个**主要适配器**，必要时增加一个**次要适配器**。按利润来源而非股票标签选择：

- 资源周期：`references/resource-cycle.md`
- 科技成长：`references/technology-growth.md`
- 制造业：`references/manufacturing.md`
- 消费：`references/consumer.md`
- 医药：`references/healthcare.md`
- 金融：`references/financial.md`
- 互联网平台：`references/internet-platform.md`

冲突时以当前利润与现金流来源为主要适配器，以最可能改变未来利润结构的业务为次要适配器。紫金→资源周期；三花→制造业+科技成长；恒瑞→医药；阿里→互联网平台。

## Phase 0–10

### Phase 0：证据盘点

列出现有数据、缺口和更新时间。证据字段必须包含 `claim/value/period/source_type/source/published_at/url/quality/status`。`quality` 使用 `primary|authoritative|secondary|weak`；`status` 使用 `verified|conflicting|unverified`。

### Phase 1：业务与盈利归因

回答卖什么、向谁卖、靠什么赚钱；拆分收入、利润、现金流的产品、地区与周期来源。

### Phase 2：行业与竞争

确定市场结构、供需位置、同业差异、成本曲线或份额变化，避免只看公司自身同比。

### Phase 3：壁垒、治理与资本配置

区分资源禀赋与运营能力，检验研发、品牌、渠道、切换成本、管理层激励、并购和分红回购的长期效果。

### Phase 4：财务质量

分析增长质量、利润率、ROE/ROIC、经营现金流、资本开支、负债、营运资本、一次性项目和会计风险。

先读取 SQLite 最新 `financial_collection_status` 和 `financial_quality_summary`；只有采集门禁为 `pass` 才将评分作为完整财务结论，`partial|blocked` 必须暴露限制并降低置信度。将问题卡和证伪条件作为财务层证据。仅当摘要缺失、过期或被年报、更正、非标审计、重大并购/监管事件实质性推翻时调用 `$financial-report-analysis`，不得重复五年审计。

### Phase 5：股东与筹码结构

核验股东户数、集中度、机构变化、解禁和增减持。筹码只能解释市场约束，不能替代基本面结论。

### Phase 6：类型适配

执行主要适配器全部问题和次要适配器的差异问题，明确领先指标及其传导链。

### Phase 7：量化与技术状态

用市场状态、500 日价量、多周期与策略 research mode 判断市场在交易什么预期；给出 signal/score/evidence/uncertainty/invalidation，不给操作建议。

### Phase 8：估值与隐含预期

选择与类型匹配的估值法，使用历史与同业作参照，反推当前估值要求收入、利润率、商品价、份额或现金流达到什么水平。

### Phase 9：情景分析

建立 bear/base/bull 三种情景。每个情景写驱动变量、传导路径、结果区间、关键假设和可观测触发器；禁止把券商预测直接当结论。

### Phase 10：综合结论与证伪

给出核心论点、最强反方论据、关键矛盾、置信度、证伪条件、待跟踪指标和 evidence gaps。使用[报告模板](references/report-template.md)。

## 持久化

报告写入 `tracking/{code}-{name}/deep-analysis-YYYY-MM-DD.md`。用 `scripts/research_snapshot.py` 将完整证据索引写为 `research_evidence`，将类型、论点、证伪、置信度和报告路径写为 `research_summary`。两者都进入现有 `stock_snapshots`，不新建数据库。

## 完成检查

- 十一个报告章节齐全，主要/次要适配器清楚。
- 每个关键结论能追到证据，来源链接、日期、quality、status 齐全。
- 至少一个真正反方论据，三情景可观测，证伪条件具体。
- 技术与策略仅解释市场状态，没有越界形成交易动作。
- 已保存两个研究快照；数据能力缺口同步到 `references/analysis-gaps.md`。
