---
name: discovery
description: 潜力股发现 — L1快照→L2评分→L3策略验证，完整三层筛选
---

# 潜力股发现

从 5000+ A 股中系统化发现值得追踪的股票。三层筛选 + 策略验证。

## 用法

`$discovery` 或用户说"潜力股""发现股票""发现机会""有什么好股票"

## 流程

严格按 `references/scenarios/discovery.md` 执行。

### Phase 1: L1 快照

```bash
source .venv/bin/activate && python src/screener.py
```

### Phase 2: L2 评分

```bash
source .venv/bin/activate && python src/screener.py --l2
```

### Phase 3: 板块扫描

```bash
source .venv/bin/activate && python src/sector_scan.py
```

### Phase 4: 确定 L3 候选

读取三个 JSON 文件，按规则筛选 10-15 只：

```
规则 A: L2 ≥ 70 分 → 自动进入
规则 B: 板块前5领头羊 ∩ L2 ≥ 55 分
规则 C: L2 55-69分 ∩ 涨幅<8% ∩ 成交>100亿 → 择优选 3-5 只
```

### Phase 5: L3 策略验证

在任务允许并行代理时，为每只候选分配独立子任务并行执行；否则逐只执行。

**Agent 标准 prompt（必须原样使用）：**

```
你是L3策略验证Agent。对 {name}({code}) 执行策略分析。

1. 读取 data/{code}/indicators.json → 判断 trend.status
2. 读取 references/skills-index.md → 按市场状态选 3-5 个策略
3. 对每个选中策略：
   a. 读取 .agents/skills/strategy-{name}/SKILL.md
   b. 按 Step 1→2→3→4 逐步执行，引用具体数据
   c. 输出 JSON: {"name":"strategy-xxx","signal":"buy|hold|sell","score":0-100,"reason":"一句话"}
4. 汇总写入 data/{code}/strategy_scan.json（code 为纯数字，不加 SZ/SH 前缀）：

{
  "code": "002463",
  "name": "沪电股份",
  "market_regime": "trending_up",
  "strategies": [
    {"name":"strategy-bull-trend","signal":"hold","score":72,"reason":"..."},
    ...
  ],
  "consensus": {"buy":0,"hold":5,"sell":0},
  "verdict": "偏多",
  "weighted_score": 57
}

策略名格式: strategy-xxx-xxx（小写+连字符，禁止下划线）
信号: buy/hold/sell（小写英文）
路径: data/{code}/strategy_scan.json（纯数字code，不加SZ/SH）
```

等全部完成后，汇总各候选得分。

### Phase 6: 最终评分和报告

```
综合分 = L2评分 × 0.4 + 策略加权 × 0.4 + 板块强度 × 0.2

排序 → 推荐前 3-5 只加入追踪池
```

写入 `tracking/sectors/YYYY-MM-DD-discovery.md`

更新 `tracking/tracklist.json` 加入推荐股票（tier: watch）

## 输出

- `data/market/screener.json`
- `data/market/screener_l2.json`
- `data/market/sector_scan.json`
- `data/{code}/strategy_scan.json`（每只 L3 候选）
- `tracking/sectors/YYYY-MM-DD-discovery.md`
- `tracking/tracklist.json`（更新）

## 完成标志

- [ ] L1+L2+板块扫描 已完成
- [ ] L3 策略验证完成（Agent 并行，每只 3-5 策略）
- [ ] 发现报告已写入
- [ ] 追踪清单已更新
