---
name: financial-report-analysis
description: Use when analyzing listed-company annual reports, interim reports, financial quality, accounting comparability, earnings quality, asset quality, cash-flow quality, related parties, or 财报排雷；不用于估值和交易决策。
---

# 财报深度解析

## Project contract

- workflow: financial-report
- consumes: `snapshot.fundamentals`, `snapshot.news`
- produces: `artifact.financial_collection_status`, `artifact.financial_quality_summary`
- policies: `DATA.QUALITY`, `SEARCH.PRIORITY`, `RESEARCH.EVIDENCE`, `DECISION.SEPARATION`

判断财报是否可信到值得继续研究。默认读取最近五年年报和最新一期季报/中报；周期、并购、重资产或存在多年异常时扩展至十年。

## 边界

- 不得输出估值、目标价、买卖、持仓、仓位或止损。
- 没有监管、法院、交易所、审计或公司正式认定，不得把风险信号写成舞弊事实。
- 官方财报优先；缺失值必须为 unavailable，禁止填零。

## Phase 0–10

**Stage A（强制，只收集）**：读取 `references/collection-protocol.md` 和 `references/research-package.md`。先建立带稳定证据编号的独立研究资料包和 `financial_collection_status`；用 EasyAnySearch 执行中英文检索矩阵，覆盖最近电话会、券商前瞻/预测调整、权威媒体、股价异动、监管、行业和同行。门禁未评估前不得评分或分析。只有链接而没有提取事实、结构化数据和适用性说明，不算完成采集。

**Stage B（门禁后分析）**：`pass` 才能完整分析；`partial` 只能给阶段性判断；`blocked` 只能报告采集结果与缺口。

**Phase 0**：确认主体、市场、财年、币种、会计与审计准则，读取已有 tracking 和快照。最近正式披露→最近电话会→最近预告/前瞻→最近监管事件→五年历史趋势；来源权威性始终高于新鲜度。
1. 收集正式财报、审计报告、附注、问询回复、修订、更正、处罚和重大公告。
2. 先理解产品、客户、供应商、地区、量价、产能和行业周期。
3. 分别标准化合并报表与母公司报表，并与 SQLite 结构化数据核对。
4. 检查政策、估计、新准则、差错更正、追溯调整和科目重分类；不可桥接则标记 not_comparable。
5. 用 `scripts/analyze_financials.py` 运行确定性规则；命中只代表调查线索。
6. 按科目分析现金、债务、应收、合同资产、存货、固定资产、在建工程、商誉、研发、投资、减值、税和关联方。
7. 做利润—现金—资产三表闭环，判断增长如何融资、利润能否转成可分配现金。
8. 检查硬门槛并进行十五维、100 分财务质量评分，禁止重复扣分。
9. 为重大问题生成 P0/P1/P2/P3 问题卡，并对严重结论做反方审查。
**Phase 10**：按报告模板写入 `tracking/{code}-{name}/financial-analysis-YYYY-MM-DD.md`，保存两个 SQLite 快照。完成前运行研究资料包校验器；核心章节必须展示数据、计算、管理层解释、外部预测、独立分析、反方和验证指标，禁止只列结论。

## 四项验证

每个重大异常必须回答：经营逻辑能否解释；会计政策/估计能否解释；现金是否支持；最终落到哪项资产或负债。

## 证据与适配

证据类型使用 `confirmed_fact|calculated_fact|third_party_data|interpretation|open_question`；可比性使用 `comparable|adjusted|not_comparable|unresolved`。A股、港股、美股和 A+H 先读取 `references/market-adapters.md`；行业阈值读取 `references/industry-adapters.md`。金融企业禁止套用工业企业应收、存货和经营现金流规则。

## 输出

读取 `references/report-template.md`。保存 `financial_report_evidence` 与 `financial_quality_summary`；后者供 `$deep-stock-analysis` 使用。评级只能是 A/B/C/D/E，结论使用“可继续研究/需加强核验/信息不足/因财务质量原则排除”。

报告开头必须展示采集截止日、最新报告期、覆盖分数、`pass|partial|blocked`、近期来源、缺失信息和 `full_analysis|stage_assessment|collection_report`。近期预测必须标记证据类别并绑定正式验证事件。

## 参考文件

- 数据与证据：`references/evidence-schema.md`、`references/normalization-contract.md`
- 信息采集：`references/collection-protocol.md`
- 资料归档：`references/research-package.md`
- 方法：`references/accounting-comparability.md`、`references/deterministic-rules.md`、`references/scoring-system.md`
- 风控：`references/issue-card-playbook.md`、`references/risk-control.md`
- 适配与报告：`references/market-adapters.md`、`references/industry-adapters.md`、`references/report-template.md`
