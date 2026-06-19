# 场景：每日巡检

## 触发

"巡检" / "观察列表" / "看看观察股" / "watchlist"

## 适用股票

tracking/tracklist.json 中 tier = "watch" 的全部股票

## 策略说明

本场景**不执行策略分析**。只做数据刷新和异动筛查。异动触发后，升级到 key-observation 或 strategy-scan 场景再跑策略。

## 步骤

### 1. 获取清单

```
Read tracking/tracklist.json → 取 tier = "watch" 的 stocks[]
```

### 2. 并行抓取数据

对每只 watch 股票并行执行：

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
source .venv/bin/activate && python src/indicators.py --code {code}
```

### 3. 异动筛查

读取每只股票的 `data/{code}/quote.json` 和 `indicators.json`，检查：

| 触发条件 | 阈值 | 含义 |
|----------|------|------|
| 涨跌幅 > 5% | +5% 或 -5% | 大阳/大阴，需分析 |
| 量比 > 2.0 | 2倍以上 | 放量异动 |
| 量比 < 0.5 | 一半以下 | 地量，可能见底 |
| RSI6 < 25 或 > 75 | 极端值 | 超卖/超买 |
| 连续3日同向 | 3连阳/阴 | 趋势形成 |

上述任一条件触发 → 该股当日需升级分析（走 key-observation 或 strategy-scan）。

### 4. 输出巡检报告

```
Write tracking/watchlist/YYYY-MM-DD-patrol.md
```

**巡检报告格式**：

```markdown
# 每日巡检 — YYYY年MM月DD日

## 概览

| 股票 | 收盘 | 涨跌 | 量比 | RSI | 状态 |
|------|------|------|------|-----|------|
| xxx  | xx   | +x%  | x.x  | xx  | 正常/异动/关注 |

## 异动股票

（仅列出触发异动条件的股票，每只2-3句话说明）

### {name} ({code})

- 异动类型：放量大涨/缩量下跌/...
- 关键价位：支撑X / 阻力X，当前距XX X%
- 建议：是否需深度分析 / 调整追踪层级 / 继续观察
```

### 5. 跟进判断

巡检发现有异动的股票：
- 若属于已知追踪板块（芯片），对比板块内其他股票 → 判断是板块共振还是个股独立行情
- 若涨幅 > 7% 且量比 > 2 → 建议升级为重点观察，走 key-observation 场景
- 若跌幅 > 7% → 检查是否有重大利空

## 完成标志

- [ ] 所有 watch 股票数据已刷新
- [ ] 巡检报告已写入 tracking/watchlist/
- [ ] 异动股已标注跟进建议（含"是否需跑策略"判断）
