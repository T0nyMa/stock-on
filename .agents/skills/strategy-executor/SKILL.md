---
name: strategy-executor
description: 标准化策略执行器 — 读取策略定义，逐步执行，输出信号+评分+依据
---

# 策略执行器

标准化执行单个策略。被 daily-report 等场景调用，确保每次策略分析都走完整流程。

## 用法

`$strategy-executor {code} strategy-{name} mode=trading|research`

省略 mode 时默认 `trading`，例如：`$strategy-executor 002050 strategy-wave-theory`。

## 流程

### Step 1: 加载策略定义

```
读取 .agents/skills/strategy-{name}/SKILL.md
```

获取该策略的分析框架（Step 1/2/3/4）。

### Step 2: 读取数据

根据策略定义的"输入"章节，读取对应数据文件：

```
SQLite 日K（`python -m src.data_access --code {code} --kind bars`）
SQLite 指标快照（`python -m src.data_access --code {code} --kind indicators`）
SQLite 行情快照（`python -m src.data_access --code {code} --kind quote`）
SQLite 新闻快照（`python -m src.data_access --code {code} --kind news`）        ← 如策略需要
SQLite 基本面快照（`python -m src.data_access --code {code} --kind fundamentals`） ← 如策略需要
```

### Step 3: 逐步执行

严格按照策略定义中的 Step 1 → Step 2 → Step 3 → Step 4 执行。

每个 Step 必须引用具体数据，不能模糊：
- ✅ "量比 1.26 > 1.2 → 放量确认"
- ❌ "量能看起来还行"

### Step 4: 输出

#### trading mode（默认，兼容原行为）

每个策略 Skill 只返回以下结构化内存结果，不自行写文件：

```json
{
  "name": "strategy-wave-theory",
  "signal": "buy",
  "score": 68,
  "reason": "C浪末端确认，44.11接近A浪低点44.5，78.6%回撤位守住"
}
```

**字段规范（严格执行）：**
- `name`: 策略名称，必须用 **小写+连字符**（`strategy-wave-theory`, `strategy-bull-trend`, `strategy-ma-golden-cross`），禁止用下划线
- `signal`: 只允许 `buy` / `hold` / `sell`（小写英文）
- `score`: 0-100 整数
- `reason`: 一句话，中文，引用具体数据

**多策略汇总**：执行器收齐可用结果后计算 `strategy_count`、原始票数（仅诊断）、归一化比例和加权分数，再由执行器独占写入登记的 `artifact.strategy_scan`：

```json
{
  "code": "002050",
  "name": "三花智控",
  "market_regime": "bearish",
  "strategies": [
    {"name": "strategy-wave-theory", "signal": "buy", "score": 68, "reason": "..."},
    {"name": "strategy-emotion-cycle", "signal": "hold", "score": 55, "reason": "..."}
  ],
  "strategy_count": 5,
  "consensus": {
    "buy": 3,
    "hold": 2,
    "sell": 0,
    "buy_ratio": 0.60,
    "hold_ratio": 0.40,
    "sell_ratio": 0.00
  },
  "weighted_score": 64,
  "verdict": "偏多"
}
```

`buy_ratio = buy / strategy_count`，`hold_ratio = hold / strategy_count`，`sell_ratio = sell / strategy_count`；三者应合计为 1（允许小数舍入误差）。`weighted_score = Σ(score × weight) / Σ(weight)`。

判定必须适应任意策略数量，原始票数不得单独决定 verdict：

```
buy_ratio >= 0.70 且 weighted_score >= 70 → 强偏多
buy_ratio >= 0.55 且 weighted_score >= 60 → 偏多
sell_ratio >= 0.55 或 weighted_score < 40 → 偏空/回避
其余 → 分歧/观望
```

策略样本或证据不足时降低置信度并披露，不为满足比例阈值补造策略结果。

**路径规范**：`data/{code}/strategy_scan.json`，code 为纯数字（如 `002050`，**不要**加 SZ/SH 前缀）

#### research mode（深度研究）

用于 `$deep-stock-analysis` 解释市场正在交易的预期。不得包含操作建议，不写 buy/hold/sell、仓位、价位或止损，也不写入 `strategy_scan.json`：

```json
{
  "name": "strategy-wave-theory",
  "mode": "research",
  "score": 68,
  "evidence": ["收盘价处于MA20下方，ADX为27"],
  "interpretation": "中期趋势偏弱，市场尚未确认盈利预期改善",
  "uncertainty": ["事件缺口可能使形态失真"],
  "invalidation": ["放量站稳MA20且相对强弱转正"]
}
```

`score` 表示策略证据强度而非投资吸引力。`evidence` 必须是具体数据；`uncertainty` 和 `invalidation` 至少各一项。

## 多策略并行

当需要执行多个策略且任务允许并行代理时，可将各策略分配为独立子任务并行执行：

```
Agent: /strategy-executor {code} strategy-wave-theory
Agent: /strategy-executor {code} strategy-emotion-cycle
Agent: /strategy-executor {code} strategy-bottom-volume
```

每个 Agent 独立返回信号、评分与依据；`$strategy-executor` 汇总归一化共识并独占持久化 `artifact.strategy_scan`。
