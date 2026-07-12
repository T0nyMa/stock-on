# tracking/ — 追踪与报告层

本目录保存人类可读报告以及当前追踪、持仓状态。机器可读路径、生产者、消费者和新鲜度以 `spec/artifacts.yaml` 为准；工作流摘要见 `references/generated/workflows.md`。

## 已登记工件

- `artifact.tracklist`：`tracking/tracklist.json`，当前追踪清单；股票数量和分层始终从文件读取，不在文档中固定。
- `artifact.position`：`tracking/{code}-{name}/position.json`，适用股票的持仓与决策上下文。
- `artifact.daily_report`：`tracking/daily/positions/{date}.md`，单文件、完整七章日报，结构使用 `references/templates/daily-report-v2.md`。
- `artifact.weekly_report`：`tracking/weekly/{week}.md`。
- `artifact.discovery_report`：`tracking/discovery/{date}.md`。

单股目录可保留研究和历史分析 Markdown；这些用户文件不是结构化数据源，不应被批量覆盖或删除。

## 执行入口

日报和周报分别执行登记的 `daily-report`、`weekly-report` 工作流，并在完成后执行 `deploy`。日报不得拆成大盘与持仓两个交付物，也不得另行生成固定数量的单股日报。七章内容、数据前置、持仓更新、提交、推送和发布门禁以 `spec/workflows/*.yaml` 为准。

分析或决策前先读现有报告、`artifact.tracklist` 和适用的 `artifact.position`。需要定量结论时使用已登记的 SQLite 快照与 `artifact.report_context`；缺失值按 `DATA.QUALITY` 保留为 `unavailable`。
