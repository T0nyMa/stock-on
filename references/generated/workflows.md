# Workflow 快速参考

本页汇总 `spec/workflows/*.yaml` 的输入、输出、策略和完成门禁。详情以 YAML 注册项为准，不要手工编辑标记区域。

<!-- BEGIN GENERATED: workflows -->
| Workflow ID | Skills | Inputs | Outputs | Policies | 完成门禁 |
|---|---|---|---|---|---|
| `daily-report` | `daily-report`<br>`deploy` | `snapshot.quote`<br>`snapshot.news`<br>`snapshot.indicators`<br>`artifact.report_context`<br>`artifact.tracklist`<br>`artifact.position`<br>`artifact.research_summary`<br>`artifact.financial_collection_status`<br>`artifact.strategy_scan` | `artifact.daily_report` | `DATA.QUALITY`<br>`SEARCH.PRIORITY`<br>`RESEARCH.EVIDENCE`<br>`DECISION.SEPARATION`<br>`PUBLISH.COMPLETE` | `DATA.REGISTERED_CURRENT`<br>`RESEARCH.SOURCES_BOUND`<br>`DECISION.ACTION_SPECIFIC`<br>`PUBLISH.PUSHED` |
| `data-preparation` | `fetch-data` | — | `database.stock_analysis`<br>`snapshot.bars`<br>`snapshot.quote`<br>`snapshot.fundamentals`<br>`snapshot.news` | `DATA.QUALITY`<br>`SEARCH.PRIORITY` | `DATA.REGISTERED_CURRENT`<br>`SEARCH.MATERIAL_FACT_VERIFIED` |
| `deep-research` | `deep-stock-analysis` | `snapshot.fundamentals`<br>`snapshot.news`<br>`artifact.financial_collection_status`<br>`artifact.financial_quality_summary` | `artifact.research_summary` | `DATA.QUALITY`<br>`SEARCH.PRIORITY`<br>`RESEARCH.EVIDENCE`<br>`DECISION.SEPARATION` | `RESEARCH.SOURCES_BOUND` |
| `deploy` | `deploy` | `artifact.daily_report` | `artifact.published_html` | `PUBLISH.COMPLETE` | `PUBLISH.PUSHED` |
| `development` | — | — | `artifact.verification_record` | `DEV.CHANGE` | `DEV.TESTS_VERIFIED` |
| `discovery` | `discovery`<br>`screener`<br>`sector-scan` | `snapshot.indicators`<br>`artifact.strategy_scan` | `artifact.discovery_report` | `DATA.QUALITY`<br>`RESEARCH.EVIDENCE` | `DATA.REGISTERED_CURRENT`<br>`RESEARCH.SOURCES_BOUND` |
| `financial-report` | `financial-report-analysis` | `snapshot.fundamentals`<br>`snapshot.news` | `artifact.financial_collection_status`<br>`artifact.financial_quality_summary` | `DATA.QUALITY`<br>`SEARCH.PRIORITY`<br>`RESEARCH.EVIDENCE`<br>`DECISION.SEPARATION` | `RESEARCH.SOURCES_BOUND` |
| `position-decision` | `decision-agent` | `snapshot.indicators`<br>`artifact.report_context`<br>`artifact.research_summary`<br>`artifact.financial_quality_summary`<br>`artifact.discovery_report`<br>`artifact.strategy_scan` | `artifact.tracklist`<br>`artifact.position` | `DATA.QUALITY`<br>`RESEARCH.EVIDENCE`<br>`DECISION.SEPARATION` | `DATA.REGISTERED_CURRENT`<br>`RESEARCH.SOURCES_BOUND`<br>`DECISION.ACTION_SPECIFIC` |
| `quant-analysis` | `tech-indicators`<br>`market-regime` | `database.stock_analysis`<br>`snapshot.bars`<br>`snapshot.quote` | `snapshot.indicators`<br>`artifact.report_context` | `DATA.QUALITY` | `DATA.REGISTERED_CURRENT` |
| `strategy-analysis` | `strategy-executor` | `snapshot.indicators` | `artifact.strategy_scan` | `DATA.QUALITY` | `DATA.REGISTERED_CURRENT` |
| `weekly-report` | `weekly-report`<br>`deploy` | `snapshot.indicators`<br>`artifact.report_context`<br>`artifact.tracklist`<br>`artifact.position`<br>`artifact.research_summary`<br>`artifact.financial_collection_status`<br>`artifact.daily_report` | `artifact.weekly_report` | `DATA.QUALITY`<br>`RESEARCH.EVIDENCE`<br>`DECISION.SEPARATION`<br>`PUBLISH.COMPLETE` | `DATA.REGISTERED_CURRENT`<br>`RESEARCH.SOURCES_BOUND`<br>`DECISION.ACTION_SPECIFIC`<br>`PUBLISH.PUSHED` |
<!-- END GENERATED: workflows -->
