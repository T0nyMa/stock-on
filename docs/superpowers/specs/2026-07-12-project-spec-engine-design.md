# Stock-On 项目规范引擎设计

## 1. 背景与目标

Stock-On同时承担Python开发、行情与财务数据准备、量化技术分析、公司深度研究、财报分析、交易决策、日报周报、发现筛选和发布。现有规范分散在`AGENTS.md`、项目Skill、场景文档、模板及各目录README中，已经出现重复规则、旧Claude路径、SQLite与JSON协议冲突、日报流程多版本并存以及Skill索引失真。

本设计建立面向Codex执行的混合规范编译器：机器可判定的路由、工作流、产物和门禁使用模块化YAML作为单一事实源；需要专业判断的分析方法继续保留在Skill和Markdown中；Python编译器负责校验、生成入口文档和运行门禁。

第一版覆盖全部核心能力：开发、数据准备、量化技术、策略分析、深度研究、财报分析、建仓与持仓决策、日报、周报、发现筛选和发布。

## 2. 设计原则

1. Codex执行优先，人类可读性作为必要兼容目标。
2. 一条强制规则只有一个权威来源，其他文档通过稳定规则ID引用。
3. 机器可判定内容结构化；专业分析和判断不硬编码进YAML。
4. 根入口保持短小，按意图渐进加载Workflow、Policy、Skill和Reference。
5. 数据真实性、证据质量、交易安全和发布完整性采用阻断门禁；非关键增强采用警告。
6. 生成区不可手工修改，人工原则区继续允许维护。
7. 迁移期间显式报告冲突，不静默兼容过期规范。

## 3. 规范优先级

从高到低：

1. 用户当次明确指令。
2. `AGENTS.md`人工核心原则。
3. `spec/policies/*.yaml`跨流程强制政策。
4. `spec/workflows/*.yaml`具体工作流契约。
5. `.agents/skills/*/SKILL.md`专业执行方法。
6. `references/`方法论、模板和背景知识。
7. 各目录`README.md`人类使用说明。

用户指令可以改变任务范围，但不能绕过数据真实性、安全和证据硬门禁。README不作为Codex权威执行规范。Skill不得重复定义全项目政策，只通过Policy ID声明依赖。

## 4. 目录与组件

```text
spec/
  project.yaml
  routes.yaml
  artifacts.yaml
  skills.yaml
  policies/
    development.yaml
    data-quality.yaml
    search.yaml
    research.yaml
    decision.yaml
    publishing.yaml
  workflows/
    development.yaml
    data-preparation.yaml
    quant-analysis.yaml
    strategy-analysis.yaml
    deep-research.yaml
    financial-report.yaml
    position-decision.yaml
    daily-report.yaml
    weekly-report.yaml
    discovery.yaml
    deploy.yaml
```

### 4.1 project.yaml

定义规范版本、项目身份、长期原则、默认运行环境和目录所有权。目录所有权明确`src/`负责数据与确定性计算、`tracking/`负责研究和报告、`strategies/`负责策略定义、`.agents/skills/`负责Agent工作流、`references/`负责方法论。

### 4.2 routes.yaml

每条路由包含稳定ID、意图模式、优先级、Workflow、Skill和必要参数。同一输入必须得到唯一最高优先级路由；并列冲突属于静态校验错误。

### 4.3 artifacts.yaml

登记正式产物的ID、路径模式、生产者、消费者、格式、schema版本、新鲜度、缺失处理和保留策略。覆盖SQLite数据库与snapshot、`report_context.json`、研究资料包、财报摘要、持仓文件、日报周报、发现报告和发布HTML。

### 4.4 skills.yaml

记录项目Skill的ID、路径、类别、关联Workflow、输入输出和边界。编译器同时扫描实际Skill目录；目录存在但未注册、注册路径失效或Skill名称冲突均报错。

### 4.5 policies

- `development.yaml`：代码修改、测试优先、数据库迁移、验证、提交和兼容性。
- `data-quality.yaml`：SQLite优先、缺失值、数据新鲜度、定量字段来源和抓取失败处理。
- `search.yaml`：AnySearch优先；额度耗尽、服务异常或结果不足时使用EasyAnySearch；搜索结果只作线索，关键事实回到一手来源核验。
- `research.yaml`：来源等级、证据库、深研与财报门禁、预测验证事件。
- `decision.yaml`：研究与交易决策分离；交易建议必须具体到价格、股数、触发和失效条件。
- `publishing.yaml`：日报周报的commit、push、HTML转换、索引更新和GitHub Pages发布。

### 4.6 workflows

每个Workflow声明ID、参数、输入、前置条件、步骤、调用的Skill、输出、Policy依赖、前置门禁、完成门禁、失败处理和可重入规则。Workflow只描述执行契约，不包含财务解释、公司类型判断或技术形态推理。

## 5. 配置接口

路由示例：

```yaml
- id: route.financial_report
  intents:
    - "财报分析 {stock}"
    - "财报深度解析 {stock}"
  workflow: financial-report
  skill: financial-report-analysis
  priority: 90
```

产物示例：

```yaml
- id: artifact.report_context
  path: data/report_context.json
  producer: quant-analysis
  consumers: [daily-report, weekly-report, position-decision]
  freshness: trading_day
  missing: block
```

Workflow示例：

```yaml
id: daily-report
inputs:
  - artifact.report_context
  - artifact.tracklist
steps:
  - data-preparation
  - quant-analysis
  - current-news-collection
  - report-render
  - deploy
policies:
  - DATA.FRESHNESS
  - SEARCH.PRIORITY
  - REPORT.AUTO_DEPLOY
gates:
  preflight: [DAILY.CONTEXT_CURRENT]
  completion: [DAILY.SEVEN_SECTIONS, PUBLISH.PUSHED]
```

## 6. 编译器与命令

实现`src/spec/`包并提供：

```bash
python -m src.spec validate
python -m src.spec generate
python -m src.spec check --workflow daily-report
python -m src.spec inspect --intent "财报分析 阿里巴巴"
```

### 6.1 validate

检查YAML Schema、唯一ID、跨文件引用、路由冲突、循环依赖、未知Skill、失效路径、产物生产者缺失、门禁严重级别、生成区漂移、旧`.claude`引用、过期JSON路径和重复强制规则。

### 6.2 generate

生成`AGENTS.md`路由区、`references/skills-index.md`清单区和`references/generated/workflows.md`工作流速查。生成内容必须位于明确标记之间：

```markdown
<!-- BEGIN GENERATED: routes -->
...
<!-- END GENERATED: routes -->
```

标记区外允许人工编辑；标记区内容与规范源不一致时，`validate`失败。生成器输出必须确定性排序，相同输入重复运行不产生diff。

### 6.3 check

对指定Workflow执行前置或完成门禁。输出规则ID、严重级别、期望状态、实际状态、证据和可执行修复命令。默认检查全部阶段，也支持`--phase preflight|completion`。

### 6.4 inspect

对自然语言意图显示最终匹配路由、Workflow、Skill、Policy、输入产物、输出产物和门禁，用于调试和审计。

## 7. 门禁模型

每条门禁使用固定严重级别：

- `block`：影响数据真实性、证据可信度、交易安全或发布完整性；失败时停止Workflow。
- `warn`：非核心覆盖、格式增强或维护问题；记录后允许继续。
- `info`：可选优化，不影响完成状态。

严重级别在规范源中固定，运行时不得临时降级。日报示例：`report_context`过期、持仓新闻未核验和发布失败为`block`；普通观察股缺少非关键媒体材料为`warn`；缺少可选图表为`info`。

## 8. 核心能力边界

### 8.1 开发

负责代码、测试、数据库迁移和数据契约，不负责股票判断。变更必须按风险运行聚焦测试和全量验证；数据库schema变化必须有显式迁移与兼容策略。

### 8.2 数据准备与量化技术

Python负责行情、K线、基本面、财务快照、指标、趋势、相对强弱、策略统计和其他确定性计算。正式报告只能消费注册产物；字段缺失时保留`unavailable`，Codex不得绕过产物自行补算。

### 8.3 深度研究

负责公司类型、行业周期、竞争壁垒、治理、筹码、估值框架与可证伪情景，不输出建仓、持仓或交易时机。

### 8.4 财报分析

负责财务质量、会计可比性、分部、利润现金资产闭环、监管与问题卡，不输出估值或交易建议。完整分析必须通过研究资料包门禁。

### 8.5 交易决策

在复用深研和财报摘要的基础上处理建仓、持仓、做T、止损和仓位，建议必须具体到价格区间、股数、触发条件和失效条件。

### 8.6 日报与周报

日报只更新当日行情、消息、技术状态和操作清单；只有重大业绩、监管、并购、核心假设变化或跨财报周期才重跑长期研究。周报汇总周内变化和下周验证，不重复生成全部日报。

### 8.7 发现与发布

发现筛选产出候选池，不直接形成建仓决定。发布只负责格式转换、索引、commit、push和Pages部署，不修改分析结论。

## 9. 数据流

```text
财报分析 ─┐
行业研究 ─┼→ 深度研究 → 交易决策 → 日报/周报 → 发布
治理研究 ─┘                    ↑
数据准备 → 量化技术 → 策略分析 ┘

全市场数据 → 筛选/板块扫描 → 发现报告 → 候选追踪 → 深度研究
```

长期研究通过SQLite snapshot和人类可读报告同时发布；日报周报优先读取结构化摘要，仅在触发条件成立时重跑长期Workflow。

## 10. 错误处理

配置或引用错误在执行前失败。数据源、搜索和发布等外部失败必须区分可重试与不可重试：短暂网络错误可以有限重试；额度耗尽按搜索Policy切换；正式数据缺失不得用弱来源或零值填补；发布失败不得把日报标记为完成。

每个失败输出统一结构：Workflow ID、Rule ID、Severity、Stage、Expected、Actual、Evidence、Remediation。警告保存在运行报告中，不能静默丢弃。

## 11. 测试体系

1. Schema单元测试：有效与无效配置样本。
2. 路由测试：唯一匹配、优先级、参数提取和冲突检测。
3. 引用与依赖测试：Skill、Artifact、Policy、Workflow和循环依赖。
4. 门禁测试：`block/warn/info`行为、数据新鲜度、证据门禁和发布状态。
5. 生成快照测试：生成区内容、确定性排序和重复运行无diff。
6. 迁移回归测试：禁止旧`.claude/skills`、过期JSON路径和重复日报契约重新出现。
7. 核心Workflow契约测试：开发、日报、周报、深研、财报、决策、发现和发布均有成功与失败样本。

## 12. 迁移计划

迁移按以下顺序完成，但第一版最终覆盖全部核心能力：

1. 建立`spec/`schema、加载器和只读`validate/inspect`。
2. 注册现有Skill、Artifact、Policy和Workflow。
3. 建立测试，暴露重复路由、旧路径和协议冲突。
4. 修复`tracking/README.md`、`strategies/README.md`、场景文件和Skill索引漂移。
5. 实现确定性`generate`，重构AGENTS和Skill索引为人工区加生成区。
6. 实现`check`并接入开发、数据、研究、财报、决策、日报周报、发现和发布。
7. 更新各Skill只引用Policy与Artifact ID，删除重复全局规则。
8. 确认没有消费者后删除过期场景和重复规范。

迁移期间，新增规则只能进入`spec/`。旧文档与`spec/`冲突时校验失败；不得长期维护双份真相。

## 13. 非目标

- 不把财务推理、公司类型分析或技术形态判断硬编码进YAML。
- 不自动生成全部Skill正文。
- 不让生成文件成为新的手工维护源。
- 不在规范引擎第一版重写行情、量化或报告业务实现。
- 不用规范引擎代替Python测试、研究证据审查或Codex专业判断。

## 14. 验收标准

- 任一支持意图通过`inspect`得到唯一执行链。
- 任一正式Artifact可追溯生产者、消费者、schema和新鲜度。
- `AGENTS.md`只保留人工核心原则和自动生成路由入口，不再复制日报正文。
- Skill索引与实际Skill目录自动同步。
- 所有跨文件引用、生成区和旧路径检查通过。
- 全部核心Workflow具有Policy、输入、输出、门禁和失败策略。
- 数据真实性、研究证据、交易安全和发布完整性规则可机器阻断。
- 全量项目测试和规范引擎测试全部通过。
