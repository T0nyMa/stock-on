# 股票研究技能矩阵与技术研究 Skill 设计

日期：2026-07-16  
状态：已获用户口头批准，等待书面规格复核

## 目标

统一股票研究与决策 Skill 的命名规范，明确基本面、财务质量、纯技术研究和交易决策的边界；新增同时支持单股和多股比较的 `stock-technical-research`，形成可被日报、周报和持仓决策复用的登记工件。

## 命名规范

核心 Skill 采用 `<object>-<evidence-domain>-<output-type>`：

| 当前名称 | 新名称 | 中文侧重点 |
|---|---|---|
| `deep-stock-analysis` | `company-fundamental-research` | 公司经营、行业、竞争、治理、估值与长期证伪 |
| `financial-report-analysis` | `financial-statement-quality` | 会计可比性、盈利、资产、现金流、关联方与财报排雷 |
| 新增 | `stock-technical-research` | 指数环境、价格路径、量价、振幅、指标与技术结构 |
| `decision-agent` | `stock-position-decision` | 汇总研究、技术和组合风险形成具体交易决策 |

旧中文意图词和旧 Skill 名称作为触发同义词保留在 description、路由与兼容测试中；不保留两套 Skill 实现目录。

## 技能矩阵

```text
确定性数据层
├── fetch-data
└── tech-indicators

市场环境层
├── market-regime
└── sector-scan

研究层
├── company-fundamental-research
├── financial-statement-quality
└── stock-technical-research

策略层
├── strategy-executor
└── strategy-*

决策层
└── stock-position-decision

报告与发布层
├── daily-report
├── weekly-report
└── deploy
```

三类研究独立形成证据，不互相代替。只有 `stock-position-decision` 可以输出交易价格、股数、仓位、触发和失效条件。

## 边界契约

### company-fundamental-research

研究公司经营状态、商业模式、行业周期、竞争壁垒、治理、估值、催化剂和可证伪长期情景。不以短期价格形态推导公司质量，不输出交易指令。

### financial-statement-quality

研究财务报表的会计可比性、盈利质量、资产质量、现金流、关联方和财务风险。不承担估值、技术分析或交易决策。

### stock-technical-research

只研究市场交易行为：指数背景、价格路径、趋势、成交量、振幅、波动、相对强弱和技术指标共振。可识别技术阶段并给出关键位、确认条件和结构证伪条件；不得输出买入、卖出、加仓、减仓、股数或仓位。

### stock-position-decision

消费基本面、财务质量、技术结构、策略和组合风险工件，形成具体价格、股数、触发、目标和失效条件。不得重新执行或隐式拼接上游研究。

## stock-technical-research 使用模式

### 单股模式

示例意图：

- “技术分析 601138”
- “分析工业富联近3个月技术结构”

输出单股完整技术研究。

### 多股比较模式

示例意图：

- “技术对比山东黄金、三花、工业富联”
- “比较600547、002050、601138的量价结构”

对每只股票执行相同口径，并输出横向比较与技术阶段排序。排序只表示技术结构相对状态，不表示投资优先级。

### 窗口与基准

- 默认窗口：90个自然日，报告实际交易日数量。
- 可选窗口：20日、60日、3个月、6个月。
- 默认基准：上证指数。
- 科技成长股附加深证成指、创业板指和科创50。
- A+H股票分别覆盖两地；数据日期或汇率缺失时不做同步比较或溢价计算。

## 数据流与工件

```text
fetch-data
    ↓
SQLite bars / quote
    ↓
tech-indicators
    ↓
snapshot.indicators + artifact.report_context
    ↓
stock-technical-research
    ↓
artifact.technical_research
    ├── daily-report / weekly-report
    └── stock-position-decision
```

新增 `artifact.technical_research`：

- 单股 Markdown：`tracking/{code}-{name}/technical/{date}.md`
- 多股 Markdown：`tracking/technical/{date}-{codes}.md`
- 结构化摘要：写入 SQLite 的 `technical_research` kind，供下游消费。

结构化摘要字段：

```text
as_of
window
benchmarks
stage
stage_confidence
price_path
trend
momentum
volume
volatility
relative_strength
support_levels
resistance_levels
confirmation_conditions
falsification_conditions
evidence_gaps
```

指数历史必须成为登记数据或工件；不得用临时联网结果形成不可追溯的量化结论。

## 七层分析框架

1. **指数环境**：区间涨跌、高低点、最大回撤、最近20日表现、量能和振幅变化。
2. **价格路径**：区间起点、阶段高点、最大回撤、阶段低点、当前位置和复权口径。
3. **趋势结构**：MA5/10/20/60、多周期状态、MACD、ADX与正负DI。
4. **动量状态**：RSI、MFI、乖离率及价格/指标背离。
5. **量价资金**：分段成交量、上涨/下跌日量能、OBV与CMF。
6. **波动结构**：平均振幅、ATR、NATR、布林带宽度及波动方向。
7. **阶段判定**：下跌加速、超卖未止跌、筑底候选、右侧确认、趋势延续。

每项定性结论必须绑定登记数值证据。最终固定输出：

- 当前技术阶段与置信度；
- 支撑和压力；
- 改善确认条件；
- 结构证伪条件；
- 数据缺口；
- 多股模式下的同口径比较。

## 阶段判定要求

| 阶段 | 最低证据要求 |
|---|---|
| 下跌加速 | 价格破位，空头趋势增强，ADX或波动上升 |
| 超卖未止跌 | 动量超卖，但价格、趋势或资金尚未确认止跌 |
| 筑底候选 | 不再创新低，均线收敛或卖压衰减，但尚未突破关键压力 |
| 右侧确认 | 突破关键压力，并有趋势强度、成交量或资金指标共振 |
| 趋势延续 | 多周期趋势一致，动能与资金未出现显著背离 |

不得把 `RSI<30`、缩量下跌、单一金叉或距高点跌幅大直接判定为底部。

## 错误与缺口处理

- 行情不足指定窗口：使用实际覆盖期并披露，不外推。
- 指数历史缺失：市场环境为 `unavailable`，停止指数联动定量结论。
- 除权除息或拆并股：统一复权口径并披露公司行动。
- A/H日期不一致：分别分析，不做同步强弱结论。
- 指标冲突：输出冲突指标和不确定性，不强制投票。
- 策略扫描过期：不得引用为当前技术证据。
- 技术数据过期：先运行登记的数据准备与指标工作流。
- 相对强弱缺少基准：保留 `unavailable`，不得用主观强弱替代。

## 路由与迁移范围

同步更新：

- `.agents/skills/` 四个核心目录；
- `spec/skills.yaml`；
- 适用的 `spec/workflows/*.yaml`；
- `spec/routes.yaml`；
- `spec/artifacts.yaml`；
- `AGENTS.md` 生成路由区；
- `references/skills-index.md` 与工作流生成文档；
- Skill 间交叉引用；
- 脚本、测试和调度提示中的 Skill ID。

中文路由保持兼容：

- “深度分析”“深研” → `company-fundamental-research`
- “财报分析”“财报排雷” → `financial-statement-quality`
- “技术分析”“技术对比”“量价结构” → `stock-technical-research`
- “建仓分析”“怎么样”“今日某股票” → `stock-position-decision`

## 验证设计

实施遵循 RED-GREEN-REFACTOR。

### 基线失败场景

在新 Skill 不存在时记录代理对以下任务的自然输出：

1. 工业富联单股三个月技术分析；检查是否把区间累计上涨误判为当前强势。
2. 山东黄金、三花、工业富联横向比较；检查是否使用不一致口径。
3. RSI低于30的股票；检查是否直接声称见底或给出交易建议。
4. 缺少指数历史、基准或A/H同步数据；检查是否猜测缺失值。

### 新 Skill 验证场景

- 单股输出包含七层框架、技术阶段、关键位、确认和证伪条件。
- 多股输出使用相同窗口、基准和指标口径。
- 缺失字段原样披露 `unavailable`。
- 输出不包含具体买卖、仓位、股数和下单指令。
- 旧中文意图正确路由到重命名后的 Skill。
- Spec、工作流、工件、Skill ID与生成文档一致。
- 新增脚本或确定性计算必须有失败测试、通过测试和完整验证记录。

## 完成标准

1. 四个 Skill 使用新名称且旧实现目录不存在。
2. `stock-technical-research` 支持单股和多股模式。
3. 指数与个股的窗口、复权和数据新鲜度可追溯。
4. 七层分析框架和五阶段判定可由结构化工件表达。
5. 纯技术研究边界由测试证明，不产生交易指令。
6. 现有中文用户意图保持兼容。
7. 项目 Spec 检查、相关单元测试和 Skill 校验全部通过。

