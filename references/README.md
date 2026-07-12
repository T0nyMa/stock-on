# 参考知识索引

`spec/` 是路由、工作流、策略、工件和门禁的机器可读事实源；本目录保存方法论、模板、补充场景和生成参考。

## 首选入口

- `references/generated/workflows.md`：各 Workflow 的 Skills、输入、输出、Policy 和完成门禁。
- `spec/artifacts.yaml`：稳定 Artifact ID、路径、存储、新鲜度和缺失语义。
- `references/templates/daily-report-v2.md`：`artifact.daily_report` 的单文件七章模板。
- `references/analysis-methodology.md`：研究与决策方法论。
- `references/screening-methodology.md`：候选筛选的专业判断框架。
- `references/skills-index.md`：Skill 与策略选择参考。

## 场景文档

`scenarios/` 只补充专业判断和用户场景，不重复定义工作流工件契约。当前保留：

- `core-position.md`、`key-observation.md`、`first-time-setup.md`：持仓与建仓判断补充，受 `position-decision` 工作流约束。
- `strategy-scan.md`：策略选择与共识解释，受 `strategy-analysis` 工作流约束。
- `daily-patrol.md`：观察清单异动巡检补充。
- `discovery.md`：`$discovery` 使用的筛选判断补充，受 `discovery` 工作流约束。

日报和周报不再维护平行场景流程，直接按注册工作流、Skill 和模板执行。

## 加载顺序

先由 `AGENTS.md` 的生成路由定位 `spec/workflows/{workflow}.yaml`，再读取其 Policy、Artifact 和 Skill；仅在需要专业判断时加载对应方法论或场景。发生冲突时，注册工作流和稳定 ID 优先于场景中的说明性文字。
