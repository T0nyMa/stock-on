# tracking/ — 追踪报告层

## 职责

存放所有追踪股票的 **人类可读分析报告**，是 Claude 分析的输入和输出。同时维护追踪清单（tracklist.json），作为股票注册的单一数据源。

## 追踪清单

`tracklist.json` — 所有追踪股票的注册表。新增/移除股票时修改此文件。

分层逻辑：
- **core（核心持仓）**：实盘持有，每日深度分析
- **key（重点观察）**：候选买入，每日跟踪
- **watch（一般观察）**：板块联动或异动跟踪，异动时深研

## 目录结构

```
tracking/
  tracklist.json                  ← 追踪清单（新增/移除股票改这个）
  README.md                       ← 本文件
  {code}-{name}/                  ← 单股追踪目录
    position.json                 ← 持仓快照（core专用）
    technical-analysis-report.md  ← 总报告（基本面 + 技术面 + 情景 + 买入方案）
    YYYY-MM-DD-analysis.md        ← 每日分析日报
  daily/
    market/YYYY-MM-DD.md          ← 大盘日报
    positions/YYYY-MM-DD.md       ← 持仓观察日报（三层）
  weekly/
    YYYY-MM-DD.md                 ← 周度总结
```

## 每日报告

由 `references/scenarios/daily-summary.md` 编排，生成两份日报：

1. **大盘总结** — 4大指数表现 + 风格定性 + 量能判断
2. **持仓观察** — 三层格式（core 详写 / key 中等 / watch 表格）

```bash
# 数据准备
python src/fetch_market.py                              # 大盘指数
python src/fetch.py --code {code} && python src/indicators.py --code {code}  # 追踪股（并行）
```

## 周度报告

由 `references/scenarios/weekly-summary.md` 编排，汇总本周日报生成周度视角。

## 文件协议

### tracklist.json

```json
{
  "updated_at": "2026-06-19",
  "stocks": [
    {
      "code": "002050",
      "name": "三花智控",
      "tier": "core",
      "scenario": "core-position",
      "has_position": true
    }
  ]
}
```

### position.json（仅 core）

```json
{
  "buy_price": 57.90,
  "shares": 4300,
  "cost": 248970,
  "current_price": 45.74,
  "unrealized_pnl": -52288,
  "stop_loss": 43.50,
  "key_levels": { "support_1": 44.50, "resistance_1": 47.48 },
  "swing_plan": { "scenario_a": {...} }
}
```

### technical-analysis-report.md

每只股票的总报告。首次建仓分析时创建，后续每日/异动时更新变化章节。

核心章节：基本信息 → 基本面PE锚定 → 技术面趋势（含策略共识矩阵） → 情景分析 → 买入/持仓方案。

### YYYY-MM-DD-analysis.md

单日分析。按对应场景文档格式输出。core 每日必写，key 每日必写，watch 异动时写。

## 分析流程

1. `python src/fetch.py --code {code}` + `python src/indicators.py --code {code}`
2. Read `tracking/{code}-{name}/` 下已有报告
3. 按 `references/scenarios/{scenario}.md` 步骤执行
4. Write 更新报告文件
