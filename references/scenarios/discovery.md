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

输出：`data/market/screener.json`（三类 10 维度，~200 只）

### Phase 2: L2 技术指标评分

```bash
source .venv/bin/activate && python src/screener.py --l2
```

输出：`data/market/screener_l2.json`（100 分制评分，约 20-30 只 ≥55 分）

### Phase 3: 板块扫描（并行）

```bash
source .venv/bin/activate && python src/sector_scan.py
```

输出：`data/market/sector_scan.json`（20 板块排名）

### Phase 4: 交叉筛选候选

Read 三个 JSON，筛选 L3 候选池：

```
规则 A: L2 ≥ 70 分 → 自动进入 L3
规则 B: 板块前 5 领头羊 ∩ L2 ≥ 55 分 → 进入 L3
规则 C: L2 可关注(55-69) ∩ 涨幅 < 8% ∩ 成交 > 100亿 → 择优选 3-5 只

去重 → 预计 10-15 只进入 L3
```

### Phase 5: L3 策略验证（Agent 并行）

对每只 L3 候选，用 Agent 工具 spawn 并行执行（run_in_background: true）：

```
Agent prompt:
  你是策略验证Agent。对 {code} {name} 执行 3-5 个策略分析。

  1. Read data/{code}/indicators.json → 确定 market state
  2. Read references/skills-index.md → 按市场状态选策略:
     - trending_up → bull-trend, ma-golden-cross, volume-breakout, dragon-head, hot-theme
     - volatile → chan-theory, box-oscillation, wave-theory, bottom-volume
     - bearish → bottom-volume, shrink-pullback, emotion-cycle, expectation-repricing
     - sector_hot → hot-theme, dragon-head, event-driven, emotion-cycle
  3. 对每个策略: Read .claude/skills/strategy-{name}/skill.md → 按Step执行 → 信号+评分+依据
  4. Write data/{code}/strategy_scan.json（含共识矩阵）

  完成后不需要汇报。
```

等所有 Agent 完成后，汇总各候选的 L2 评分 + 板块排名 + 策略共识。

### Phase 6: 生成发现报告

交叉筛选：

```
L3 评分 = L2评分 × 0.4 + 策略加权评分 × 0.4 + 板块强度归一化 × 0.2

排序 → 推荐前 3-5 只加入追踪池
```

Write `tracking/sectors/YYYY-MM-DD-discovery.md`，包含：
- 候选排名表（L2分 + 策略共识 + 板块）
- 推荐入池（2-4 只）
- 建议操作（等回调/立即关注）

## 输出

```
data/market/screener.json              ← L1
data/market/screener_l2.json           ← L2
data/market/sector_scan.json           ← 板块扫描
data/{code}/strategy_scan.json         ← L3 策略验证（每只候选）
tracking/sectors/YYYY-MM-DD-discovery.md ← 发现报告
```

## 完成标志

- [ ] L1 全市场扫描完成
- [ ] L2 技术评分完成
- [ ] 板块扫描完成
- [ ] L3 候选已筛选（10-15只）
- [ ] L3 策略验证完成（每只 3-5 策略，Agent 并行）
- [ ] 发现报告已写入
- [ ] 推荐 2-4 只加入追踪池（更新 tracklist.json）
