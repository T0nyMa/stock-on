# 场景：潜力股发现（完整三层筛选 + 策略验证）

## 触发

"潜力股" / "发现股票" / "发现机会" / "discovery" / "有什么好股票"

## 前置

无（本场景包含数据准备）

## 步骤

### Phase 1: L1 全市场快照

```bash
source .venv/bin/activate && python src/screener.py
```

候选快照仅作为 `discovery` 工作流的中间证据；登记输入、输出与门禁见 `references/generated/workflows.md`。

### Phase 2: L2 技术指标评分

```bash
source .venv/bin/activate && python src/screener.py --l2
```

形成技术评分候选集；候选规模由当日数据决定，不固定数量。

### Phase 3: 板块扫描（并行）

```bash
source .venv/bin/activate && python src/sector_scan.py
```

形成板块强度证据；覆盖范围由当前配置决定。

### Phase 4: 交叉筛选候选

读取当前扫描证据，筛选 L3 候选池：

```
规则 A: L2 ≥ 70 分 → 自动进入 L3
规则 B: 板块前 5 领头羊 ∩ L2 ≥ 55 分 → 进入 L3
规则 C: L2 可关注(55-69) ∩ 涨幅 < 8% ∩ 成交 > 100亿 → 按证据强度择优

去重后进入 L3；不得为凑固定数量降低证据门槛。
```

### Phase 5: L3 策略验证（Agent 并行）

对每只 L3 候选，在任务允许并行代理时并行执行；否则顺序执行：

```
Agent prompt:
  你是策略验证Agent。对 {code} {name} 执行覆盖主要证据维度的策略分析。

  1. 读取 SQLite 指标快照（`python -m src.data_access --code {code} --kind indicators`） → 确定 market state
  2. 读取 references/skills-index.md → 按市场状态选策略:
     - trending_up → bull-trend, ma-golden-cross, volume-breakout, dragon-head, hot-theme
     - volatile → chan-theory, box-oscillation, wave-theory, bottom-volume
     - bearish → bottom-volume, shrink-pullback, emotion-cycle, expectation-repricing
     - sector_hot → hot-theme, dragon-head, event-driven, emotion-cycle
  3. 对每个策略: 读取 .agents/skills/strategy-{name}/SKILL.md → 按Step执行 → 信号+评分+依据
  4. 通过 `strategy-analysis` 产出已登记的 `artifact.strategy_scan`（含共识矩阵）

  完成后不需要汇报。
```

等所有 Agent 完成后，汇总各候选的 L2 评分 + 板块排名 + 策略共识。

### Phase 6: 生成发现报告

交叉筛选：

```
L3 评分 = L2评分 × 0.4 + 策略加权评分 × 0.4 + 板块强度归一化 × 0.2

排序后推荐满足门槛的候选加入追踪池
```

写入 `artifact.discovery_report`，实际路径由 `spec/artifacts.yaml` 登记，包含：
- 候选排名表（L2分 + 策略共识 + 板块）
- 推荐入池：仅保留达到证据与综合评分门槛、且未超过当前追踪容量的候选
- 建议操作（等回调/立即关注）

## 输出

- `snapshot.indicators`：登记的当前指标输入
- `artifact.strategy_scan`：L3 策略验证证据
- `artifact.discovery_report`：最终发现报告

## 完成标志

- [ ] L1 全市场扫描完成
- [ ] L2 技术评分完成
- [ ] 板块扫描完成
- [ ] L3 候选已按证据门槛筛选
- [ ] L3 策略验证完成（覆盖主要证据维度；任务允许时并行）
- [ ] 发现报告已写入
- [ ] 达到证据/评分门槛且追踪容量允许的候选已建议加入追踪池；无合格候选时允许空推荐
