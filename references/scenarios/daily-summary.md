# 场景：每日追踪报告

## 触发

"日报" / "今日总结" / "今天市场怎么样" / "daily report"

## 前置

无（本场景包含数据准备）

## 步骤

### Phase 1: 数据准备（主进程）

**1a. 大盘指数**

```bash
source .venv/bin/activate && python src/fetch_market.py
```

**1b. 追踪股数据（7只并行）**

```
Read tracking/tracklist.json → 取全部 stocks[]
对每只 stock 并行:
  bash: source .venv/bin/activate && python src/fetch.py --code {code}
  bash: source .venv/bin/activate && python src/indicators.py --code {code}
```

### Phase 2: 并行生成报告（全部股票单股日报 + 汇总）

**子任务 A — 大盘总结**

输入：`data/market/index.json`

输出：`tracking/daily/market/YYYY-MM-DD.md`

格式：
```markdown
# 大盘总结 — YYYY年MM月DD日（周X）

## 主要指数
| 指数 | 收盘 | 涨跌 | 成交额 | 5日趋势 |
|------|------|------|--------|---------|
| 上证 | 4090 | -0.4% | 658亿手 | +2.1% |
| 深证 | 16031 | +0.9% | XXX | +1.8% |
| 创业板 | 4252 | +2.1% | XXX | +5.2% |
| 科创50 | 1912 | +3.8% | XXX | +7.3% |

## 今日特征
- 风格定性：科技成长领涨 / 权重拖累 / 普涨 / 分化（选一）
- 成交额 vs 5日均量：放量 / 缩量 / 持平
- 最强指数：科创50 (+3.8%)
- 最弱指数：上证 (-0.4%)

## 与昨日对比
- 方向：延续 / 反转 — 如"科创50连续3日上涨，加速中"
- 量能变化
- 备注：如"上证受银行拖累走弱，但个股赚钱效应好"
```

**子任务 B — 核心持仓单股日报（core: 3-5 策略）**

对 tier = "core" 的每只股票，按 `references/scenarios/core-position.md` 步骤执行：
- Read 已有报告和 position.json
- 按市场状态从 skills-index 选 3-5 个策略，轻量执行
- Write `tracking/{code}-{name}/YYYY-MM-DD-analysis.md`
- Write 更新 `position.json` 和 `technical-analysis-report.md`

**子任务 C — 重点观察单股日报（key: 2-3 策略）**

对 tier = "key" 的每只股票，按 `references/scenarios/key-observation.md` 步骤执行：
- Read 已有报告
- 按市场状态从 skills-index 选 2-3 个策略，轻量执行
- Write `tracking/{code}-{name}/YYYY-MM-DD-analysis.md`
- Write 更新 `technical-analysis-report.md`

**子任务 D — 一般观察单股日报（watch: 1-2 策略）**

对 tier = "watch" 的每只股票：
- Read `data/{code}/indicators.json` + `quote.json`
- 按市场状态从 skills-index 选 1-2 个策略，轻量执行
- Write `tracking/{code}-{name}/YYYY-MM-DD-analysis.md`

**子任务 E — 持仓观察汇总**

输出：`tracking/daily/positions/YYYY-MM-DD.md`

格式（三层）：
```markdown
# 持仓观察日报 — YYYY年MM月DD日

## ★ 核心持仓

### {name}（{code}）
- 收盘：XX | 涨跌：±X% | 量比：X.X | 换手：X%
- 均线：MA5(X.X) | 趋势：XX(强度X)
- RSI6：XX | MACD HIST：XX
- 关键价位：止损XX（触发/未触发）| 支撑XX（守住/击穿）
- 策略信号：X买 Y持（列出3-5策略共识）
- 操作：[持有/减仓/加仓] — 具体指令

## ★ 重点观察

### {name}（{code}）
- 收盘：XX | 涨跌：±X% | 量比：X.X
- 趋势：XX | RSI：XX
- 策略信号：X买 Y持
- 买入条件：到位/靠近/远离
- 操作：[观察/准备买入] — 具体条件

## 一般观察
| 股票 | 收盘 | 涨跌 | 量比 | RSI | 状态 |
|------|------|------|------|-----|------|
| xxx  | xx   | +x%  | x.x  | xx  | 正常/异动 |
| xxx  | xx   | +x%  | x.x  | xx  | 正常/异动 |

*异动定义：涨跌>5% 或量比>2 或 RSI<25 或 RSI>75*
```

### Phase 3: 呈现

日报生成后，向用户呈现要点：

1. 大盘一句话定性
2. 核心持仓一句话（涨跌 + 操作建议）
3. 异动提醒（如有）
4. 文件路径提示

## 输出文件

```
tracking/daily/market/YYYY-MM-DD.md              ← 大盘总结
tracking/daily/positions/YYYY-MM-DD.md           ← 持仓观察汇总
tracking/{code}-{name}/YYYY-MM-DD-analysis.md    ← 全部7只，单股日报
```

## 完成标志

- [ ] fetch_market.py 已执行
- [ ] 7只追踪股 fetch + indicators 已完成
- [ ] 大盘总结已写入
- [ ] 7只单股日报已写入（core: 3-5策略 / key: 2-3策略 / watch: 1-2策略）
- [ ] 持仓观察汇总日报已写入（三层格式）
