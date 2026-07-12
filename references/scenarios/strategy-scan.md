# 场景：多策略共识扫描

## 触发

"扫描策略 {code}" / "策略怎么看 {code}" / "{code} 用哪些策略"

## 适用

任意有数据的股票

## 前置

执行 `strategy-analysis` 工作流；前置数据和完成门禁见 `references/generated/workflows.md`。

## 步骤

### 1. 判断市场状态

读取已登记的 `snapshot.indicators`（运行 `python -m src.data_access --code {code} --kind indicators`），用 `trend.status` 和 `trend.ma_alignment` 判断状态。缺失字段按 `DATA.QUALITY` 披露，不使用未登记的旁路文件降级。

### 2. 选择策略

读取 `references/skills-index.md` → "按市场状态选策略"表。

根据市场状态选择足以覆盖主要证据维度的策略；数量由当前状态和可用数据决定。

### 3. 执行策略

对每个选中的策略，读取 `.agents/skills/strategy-{name}/SKILL.md` 获取分析框架，然后：

1. 读取 SQLite 日K（运行 `python -m src.data_access --code {code} --kind bars`）, `SQLite 指标快照`, `SQLite 行情快照`（按策略需要）
2. 按策略框架的 Step 逐步分析
3. 输出：信号（buy/hold/sell）+ 评分（0-100）+ 关键依据（一句话）

策略权重参考（decision-agent 汇总用）：

| 类型 | 权重 | 包含策略 |
|------|------|---------|
| 趋势类 | 1.0 | ma-golden-cross, bull-trend |
| 量价类 | 1.0 | volume-breakout, shrink-pullback, bottom-volume |
| 形态类 | 0.9 | chan-theory, box-oscillation, wave-theory |
| 题材类 | 0.8 | hot-theme, event-driven, emotion-cycle |
| 基本面类 | 0.7 | growth-quality, expectation-repricing |
| 其他 | 0.9 | dragon-head, one-yang-three-yin |

### 4. 构建共识矩阵

```markdown
| 策略 | 类型 | 信号 | 评分 | 关键依据 |
|------|------|------|------|---------|
| 均线金叉 | 趋势 | buy | 72 | MA5上穿MA10, 量比1.2 |
| 多头趋势 | 趋势 | hold | 60 | 短期均线缠绕 |
| 放量突破 | 量价 | hold | 55 | 量能不足 |
| 缠论 | 形态 | buy | 68 | 底背驰+二买 |
| 热点题材 | 题材 | buy | 75 | 板块共振 + 放量 |
| 情绪周期 | 题材 | hold | 50 | 冰点末期但未确认 |
| 波浪理论 | 形态 | hold | 58 | C浪末端待确认 |
```

### 5. 共识判断

```
buy ≥ 5    → 强买入
buy 4      → 偏多
buy ≤ 3 且 sell ≤ 2 → 震荡/观望
sell ≥ 4   → 减仓/回避
```

加权评分 = Σ(score × weight) / Σ(weight)

### 6. 输出

```
写入 `artifact.strategy_scan`；实际路径与缺失语义以 `spec/artifacts.yaml` 为准。
```

```json
{
  "code": "002050",
  "updated_at": "...",
  "market_regime": "bearish",
  "strategies_used": ["shrink-pullback", "bottom-volume", "emotion-cycle", ...],
  "consensus": {"buy": 3, "hold": 4, "sell": 0},
  "verdict": "偏多",
  "weighted_score": 62,
  "details": "共识矩阵 Markdown"
}
```

异动时同步更新 `tracking/{code}-{name}/technical-analysis-report.md` 技术面章节。

## 完成标志

- [ ] 市场状态已由当日 `snapshot.indicators` 确定，或缺失已明确披露
- [ ] 匹配策略已按 skills-index 映射执行
- [ ] 共识矩阵已构建
- [ ] `artifact.strategy_scan` 已写入或按缺失语义披露
