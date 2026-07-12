# 现有能力集成契约

- 数据：只调用 `src/fetch.py`、`src/indicators.py` 和 `src.data_access`/`MarketDataStore`，不复制抓取与指标公式。
- 量化：直接消费 500 日、多周期、相对强弱、ATR/ADX/OBV/MFI/CMF 和校准结果。
- 策略：`market-regime` 负责路由；`strategy-executor mode=research` 输出研究解释。技术信号不是企业质量评分。
- 消息：EasyAnySearch 负责检索，最终报告必须回到公告、交易所、公司官网或权威数据源核验。
- 决策：不调用 `decision-agent`；建仓与持仓场景消费 `research_summary` 后自行叠加时机与仓位规则。
- 报告：日报/周报读取最近 summary，仅在重大业绩/监管/并购/核心假设变化或季度刷新时触发完整深研。

快照 `research_evidence` 保存证据清单；`research_summary` 保存 `company_type/thesis/falsification/confidence/source_report`。schema_version 当前为 1。
