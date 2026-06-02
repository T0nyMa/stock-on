# Stock-On: Claude Code 驱动的多 Agent 股票分析系统

## 项目简介

基于 Claude Code 多 Agent 架构的股票分析系统。**Python 只负责数据抓取和技术指标计算，Claude Agent 负责所有分析决策。**
Agent 之间通过 `data/{code}/` 下的 JSON 文件通信。

## 目录结构

```
src/              # Python 数据处理层（数据抓取 + 技术指标）
strategies/       # YAML 策略定义
data/{code}/      # 数据落地 + Agent 间通信
.claude/skills/   # Claude Code Skill 定义
```

## 核心流程

当你收到 "分析 {股票代码}" 的指令时，按以下顺序执行：

### Phase 1: 数据准备（Python 脚本，非 Agent）
1. 运行 `source .venv/bin/activate && python src/fetch.py --code {code}` — 抓取行情到 `data/{code}/`
2. 运行 `source .venv/bin/activate && python src/indicators.py --code {code}` — 计算指标到 `data/{code}/indicators.json`

### Phase 2: 市场状态识别（Claude Agent）
3. 调用 `/market-regime {code}` Skill

### Phase 3: 并行策略分析（多 Agent）
4. 读取 `data/{code}/regime.json` 获取 `recommended_strategies`
5. 取前 3 个策略，同时用 Agent 工具 spawn 并行执行（设置 run_in_background: true）：
   - `/strategy-ma-golden-cross {code}`      # 均线金叉
   - `/strategy-volume-breakout {code}`      # 放量突破
   - `/strategy-bull-trend {code}`           # 多头趋势
   - `/strategy-chan-theory {code}`          # 缠论
   - `/strategy-hot-theme {code}`            # 热点题材
   - `/strategy-shrink-pullback {code}`      # 缩量回调
   - `/strategy-dragon-head {code}`          # 龙头股
   - `/strategy-box-oscillation {code}`      # 箱体震荡
   - `/strategy-growth-quality {code}`       # 成长质量
   - `/strategy-event-driven {code}`         # 事件驱动
   - `/strategy-emotion-cycle {code}`        # 情绪周期
   - `/strategy-expectation-repricing {code}` # 预期重估
   - `/strategy-wave-theory {code}`          # 波浪理论
   - `/strategy-bottom-volume {code}`        # 地量
   - `/strategy-one-yang-three-yin {code}`   # 一阳三阴

### Phase 4: 决策汇总（Claude Agent）
6. 等所有策略 Agent 完成后，调用 `/decision-agent {code}` Skill

### Phase 5: 呈现
7. 将 decision.json 中的 final_report 呈现给用户

## 多股票分析

分析多只股票时，每只独立执行 Phase 1-4。可在 Phase 1 对多只股票串行（数据抓取需要网络稳定），Phase 3 再并行。

## 单策略直调

用户也可以直接指定单个策略分析：
- `/strategy-chan-theory 000001` — 仅用缠论
- `/strategy-wave-theory AAPL` — 仅用波浪理论

## 可用 Skills

| Phase | Skill | 类型 |
|-------|-------|------|
| 1 | fetch-data | Python 脚本 |
| 1 | tech-indicators | Python 脚本 |
| 2 | market-regime | Claude Agent |
| 3 | strategy-ma-golden-cross | Claude Agent |
| 3 | strategy-volume-breakout | Claude Agent |
| 3 | strategy-bull-trend | Claude Agent |
| 3 | strategy-chan-theory | Claude Agent |
| 3 | strategy-hot-theme | Claude Agent |
| 3 | strategy-shrink-pullback | Claude Agent |
| 3 | strategy-dragon-head | Claude Agent |
| 3 | strategy-box-oscillation | Claude Agent |
| 3 | strategy-growth-quality | Claude Agent |
| 3 | strategy-event-driven | Claude Agent |
| 3 | strategy-emotion-cycle | Claude Agent |
| 3 | strategy-expectation-repricing | Claude Agent |
| 3 | strategy-wave-theory | Claude Agent |
| 3 | strategy-bottom-volume | Claude Agent |
| 3 | strategy-one-yang-three-yin | Claude Agent |
| 4 | decision-agent | Claude Agent |
