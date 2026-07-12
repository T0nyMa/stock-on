# strategies/ — 策略定义层

本目录的 YAML 保存自然语言策略框架；实际可用策略清单与元数据以 `spec/strategies.yaml` 为事实源，不在本文固定数量。

每个策略由 `.agents/skills/strategy-{name}/SKILL.md` 执行。统一编排入口是 `$strategy-executor`，对应 `strategy-analysis` 工作流；其输入为已登记的 `snapshot.indicators`，聚合输出为 `artifact.strategy_scan`。路径、生产者、消费者和缺失语义见 `spec/artifacts.yaml`。

策略框架保留专业判断空间，但不得绕过 `DATA.QUALITY`：先取得当日登记指标，再给出信号、评分、证据与失效条件。策略选择参考 `references/skills-index.md`；工作流输入、输出与完成门禁参考 `references/generated/workflows.md`。
