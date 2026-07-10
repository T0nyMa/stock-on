# ref-repo 对齐差距分析报告

**日期**: 2026-06-02

## 已对齐（无差距）

| 模块 | 状态 |
|------|------|
| `data_provider/` — 10+ fetchers, 优先级/fallback | ✅ 逐字节一致 |
| `stock_analyzer.py` — 趋势/均线/MACD/RSI/量能 | ✅ 15/15 字段逐位匹配 |
| `search_service.py` — 多引擎新闻搜索 | ✅ 一致 |
| `enums.py`, `report_language.py` | ✅ 一致 |
| `utils/sanitize.py`, `utils/data_processing.py` | ✅ 一致 |

## 关键差距（需立即修复）

| 模块 | 缺失能力 | 严重度 |
|------|---------|:---:|
| `analyzer.py` | LLM分析层（GeminiAnalyzer + AnalysisResult） | **致命** |
| `core/pipeline.py` | 分析流水线编排 | **致命** |
| `market_analyzer.py` | 大盘复盘分析 | **致命** |
| `core/market_profile.py` | 各市场配置（CN/US/HK） | **致命** |
| `storage.py` + `repositories/` | 数据库持久化 | **致命** |
| `schemas/report_schema.py` | 分析报告 Pydantic Schema | **致命** |
| `config.py` | LLM key/搜索key/数据库配置缺失 | **致命** |
| `services/analysis_context_builder.py` | 分析上下文构建 | 高 |
| `core/trading_calendar.py` | 交易时段感知 | 高 |
| `services/history_loader.py` | 历史数据缓存加载 | 高 |
| `core/market_strategy.py` | 策略蓝图（攻/守/均衡） | 中 |
| `services/run_diagnostics.py` | 全流程诊断追踪 | 中 |

## 跳过（用户指定不需要）

- notification/notification_sender — 通知推送
- bot/ — 机器人
- api/ + webui — Web界面
- apps/ — 前端/桌面端
- agent/ — 多 Agent 系统（由 Codex 承担）
- alert_* — 告警系统
- backtest_* — 回测
- portfolio_* — 持仓管理
- scheduler.py — 定时任务
- image_stock_extractor.py — 图片识别
- social_sentiment_service.py — 美股舆情

## 修复状态 (2026-06-02)

| 模块 | 状态 | 备注 |
|------|:---:|------|
| Config (LLM/search/DB) | ✅ | 完整 ref-repo config + data_dir |
| storage.py + repositories | ✅ | 从 ref-repo 复制 |
| schemas/ | ✅ | Pydantic schema 完整 |
| core/trading_calendar.py | ✅ | 交易时段感知 |
| core/market_profile.py | ✅ | CN/US/HK 配置 |
| core/market_strategy.py | ✅ | 策略蓝图 |
| market_analyzer.py | ✅ | 大盘复盘分析 |
| analyzer.py (LLM) | ✅ | GeminiAnalyzer + AnalysisResult |
| core/pipeline.py | ✅ | 编排流水线 |
| services/analysis_context_builder.py | ✅ | 分析上下文构建 |
| services/history_loader.py | ✅ | 历史数据缓存 |
| notification (stub) | ✅ | 满足 pipeline 导入 |
| bot/models (stub) | ✅ | 满足 pipeline 导入 |
| agent/ (minimum) | ✅ | llm_adapter + defaults + protocols |

## 当前状态

- 33 tests pass
- 端到端 pipeline: fetch → indicators → full analysis chain 可用
- 15/15 技术指标字段与 ref-repo 逐位匹配
