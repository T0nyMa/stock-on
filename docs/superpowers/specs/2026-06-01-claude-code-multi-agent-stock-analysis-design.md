# Claude Code 驱动的多 Agent 股票分析系统（设计方案）

## 1. 概述

将 [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) 项目改造为 **Claude Code 驱动的多 Agent 股票分析系统**。

**核心理念**：Python 负责数据密集型任务（行情抓取、技术指标计算），Claude Agent 负责分析决策（策略解读、信号判断、风险识别）。Agent 之间通过 JSON 文件通信，无共享内存状态。

**裁剪范围**：保留数据源能力和股票分析能力，去掉 Web UI、Bot 机器人、消息通知推送三层。

## 2. 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                    Claude Code (总调度器)                          │
│  CLAUDE.md 定义流程 → Agent tool spawn 子 Agent                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Phase 1: 数据准备                                                │
│  ┌──────────────────────┐  ┌──────────────────┐                  │
│  │ fetch-data (Python)  │  │ tech-indicators  │                  │
│  │ → 行情抓取 + 落盘    │  │ (Python) → 技术指 │                  │
│  │ → data/{code}/*.json │  │ 标 → indicators   │                  │
│  └──────────────────────┘  └──────────────────┘                  │
│                           ↓                                       │
│  Phase 2: 市场状态 & 策略匹配                                      │
│  ┌────────────────────────────────────────────┐                  │
│  │ market-regime (Claude Agent)                │                  │
│  │ → 读取 indicators.json                      │                  │
│  │ → 判断市场状态 (trending_up/volatile/...)    │                  │
│  │ → 匹配 YAML 策略列表                          │                  │
│  └────────────────────────────────────────────┘                  │
│                           ↓                                       │
│  Phase 3: 并行策略分析 (多 Agent)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │均线金叉   │ │放量突破   │ │热点题材   │ │缠论      │ ...        │
│  │Claude    │ │Claude    │ │Claude    │ │Claude    │            │
│  │Agent     │ │Agent     │ │Agent     │ │Agent     │            │
│  │读JSON    │ │读JSON    │ │读JSON    │ │读JSON    │            │
│  ↓          ↓ ↓          ↓ ↓          ↓ ↓          ↓            │
│  data/{code}/strategy_*.json (各策略输出)                         │
│                           ↓                                       │
│  Phase 4: 决策汇总                                                │
│  ┌────────────────────────────────────────────┐                  │
│  │ decision-agent (Claude Agent)               │                  │
│  │ → 读所有 strategy_*.json                     │                  │
│  │ → 加权汇总 → 决策仪表盘 (Markdown)          │                  │
│  └────────────────────────────────────────────┘                  │
│                           ↓                                       │
│  最终结果呈现给用户                                                │
└──────────────────────────────────────────────────────────────────┘
```

## 3. 目录结构

```
stock-on/
│
├── python/                          # Python 数据处理层
│   ├── __init__.py
│   ├── config.py                    # 精简配置（剥离 notification 依赖）
│   ├── storage.py                   # SQLAlchemy + SQLite
│   ├── logging_config.py            # 日志配置
│   ├── enums.py                     # 枚举定义
│   ├── report_language.py           # 报告国际化
│   ├── data_provider/               # 多源行情获取（完整保留原项目）
│   │   ├── __init__.py
│   │   ├── base.py                  # DataFetcherManager + 标准化
│   │   ├── akshare_fetcher.py
│   │   ├── efinance_fetcher.py
│   │   ├── tushare_fetcher.py
│   │   ├── pytdx_fetcher.py
│   │   ├── baostock_fetcher.py
│   │   ├── yfinance_fetcher.py
│   │   ├── longbridge_fetcher.py
│   │   ├── realtime_types.py
│   │   ├── fundamental_adapter.py
│   │   ├── us_index_mapping.py
│   │   └── ...
│   ├── stock_analyzer.py            # 技术分析引擎
│   ├── search_service.py            # 新闻搜索（可选）
│   ├── fetch.py                     # 统一抓取入口
│   └── indicators.py                # 技术指标计算入口
│
├── strategies/                      # YAML 策略定义（原项目沿用）
│   ├── ma_golden_cross.yaml
│   ├── chan_theory.yaml
│   ├── volume_breakout.yaml
│   ├── hot_theme.yaml
│   ├── bull_trend.yaml
│   ├── shrink_pullback.yaml
│   ├── dragon_head.yaml
│   ├── box_oscillation.yaml
│   ├── growth_quality.yaml
│   ├── event_driven.yaml
│   ├── emotion_cycle.yaml
│   ├── expectation_repricing.yaml
│   ├── wave_theory.yaml
│   ├── bottom_volume.yaml
│   ├── one_yang_three_yin.yaml
│   └── README.md
│
├── data/                            # 数据落地（Agent 间共享）
│   └── {stock_code}/
│       ├── kline.json               # K线（近60日）
│       ├── quote.json               # 实时行情
│       ├── fundamentals.json        # 基本面
│       ├── indicators.json          # 技术指标
│       ├── news.json                # 新闻舆情
│       ├── regime.json              # 市场状态
│       ├── strategy_*.json          # 各策略 Agent 输出
│       └── decision.json            # 决策汇总输出
│
├── .claude/
│   └── skills/
│       ├── fetch-data/              # Phase 1: 数据抓取
│       ├── tech-indicators/         # Phase 1: 技术指标
│       ├── market-regime/           # Phase 2: 市场状态识别
│       ├── strategy-ma-golden-cross/ # Phase 3: 均线金叉
│       ├── strategy-volume-breakout/ # Phase 3: 放量突破
│       ├── strategy-chan-theory/    # Phase 3: 缠论
│       ├── strategy-hot-theme/      # Phase 3: 热点题材
│       ├── strategy-bull-trend/     # Phase 3: 多头趋势
│       ├── strategy-shrink-pullback/# Phase 3: 缩量回调
│       ├── strategy-dragon-head/    # Phase 3: 龙头股
│       ├── strategy-box-oscillation/# Phase 3: 箱体震荡
│       ├── strategy-growth-quality/ # Phase 3: 成长质量
│       ├── strategy-event-driven/   # Phase 3: 事件驱动
│       ├── strategy-emotion-cycle/  # Phase 3: 情绪周期
│       ├── strategy-expectation-repricing/ # Phase 3: 预期重估
│       ├── strategy-wave-theory/    # Phase 3: 波浪理论
│       ├── strategy-bottom-volume/  # Phase 3: 地量
│       ├── strategy-one-yang-three-yin/ # Phase 3: 一阳三阴
│       └── decision-agent/          # Phase 4: 决策汇总
│
└── CLAUDE.md                        # 编排流程定义
```

## 4. 数据合约（Agent 间接口）

### 4.1 Python → Agent（输入）

```json
// data/{code}/kline.json
{
  "code": "600519",
  "name": "贵州茅台",
  "market": "SH",
  "updated_at": "2026-06-01T15:30:00+08:00",
  "kline": [
    {"date": "2026-05-01", "open": 1800.0, "high": 1820.0, "low": 1790.0,
     "close": 1810.0, "volume": 2500000, "amount": 4.5e9, "pct_chg": 0.85}
  ]
}

// data/{code}/indicators.json
{
  "ma": {"ma5": 1805.0, "ma10": 1790.0, "ma20": 1760.0, "ma60": 1700.0},
  "macd": {"dif": 12.5, "dea": 10.2, "hist": 2.3},
  "rsi": {"rsi6": 62.0, "rsi12": 55.0, "rsi24": 48.0},
  "volume": {"ma5_vol": 2200000, "volume_ratio": 1.15},
  "boll": {"upper": 1850.0, "mid": 1760.0, "lower": 1670.0},
  "bias": {"bias5": 0.28, "bias10": 1.12, "bias20": 2.84},
  "chip": {"concentration": 12.5, "profit_ratio": 65.0, "avg_cost": 1750.0},
  "trend": {
    "status": "bull",
    "ma_alignment": "MA5>MA10>MA20",
    "support_levels": [1790.0, 1760.0],
    "resistance_levels": [1820.0, 1850.0]
  }
}

// data/{code}/quote.json
{
  "price": 1810.0, "pct_chg": 0.85, "volume": 2500000,
  "turnover_rate": 0.15, "pe": 25.3, "pb": 8.1, "market_cap": 22000
}
```

### 4.2 Agent → Agent（中间输出）

```json
// data/{code}/regime.json (market-regime Agent 输出)
{
  "regime": "trending_up",
  "confidence": 0.85,
  "reasoning": "MA5>MA10>MA20 多头排列，MACD 零轴上方运行",
  "recommended_strategies": [
    {"name": "ma_golden_cross", "priority": 20, "reason": "多头趋势下金叉信号可靠"},
    {"name": "volume_breakout", "priority": 30, "reason": "趋势向上时突破信号有效"},
    {"name": "bull_trend", "priority": 15, "reason": "当前处于强势多头"},
    {"name": "shrink_pullback", "priority": 40, "reason": "乖离率偏低，可能回踩"},
    {"name": "dragon_head", "priority": 50, "reason": "龙头股效应"}
  ]
}

// data/{code}/strategy_ma_golden_cross.json (策略 Agent 输出)
{
  "strategy": "ma_golden_cross",
  "display_name": "均线金叉",
  "stock_code": "600519",
  "signal": "buy",
  "score": 75,
  "confidence": 0.8,
  "reasoning": "MA5 近 2 日上穿 MA10，MACD 零轴上方金叉，量比 1.3 配合良好",
  "key_levels": {"support": 1790, "resistance": 1820, "entry": 1805, "stop_loss": 1760},
  "risk_flags": ["乖离率偏低需等待回踩"],
  "details": "详细分析文本..."
}
```

### 4.3 Agent → 用户（最终输出）

```json
// data/{code}/decision.json
{
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "overall_signal": "buy",
  "overall_score": 72,
  "strategies_used": ["ma_golden_cross", "volume_breakout", "bull_trend"],
  "weighted_scores": {
    "ma_golden_cross": 75,
    "volume_breakout": 68,
    "bull_trend": 80
  },
  "key_levels": {"support": 1790, "resistance": 1830, "entry": 1800, "stop_loss": 1760},
  "risk_flags": ["主力资金连续三日流出"],
  "catalysts": ["白酒板块旺季预期", "北向资金持续增持"],
  "final_report": "## 决策仪表盘\n\n**贵州茅台 (600519)**\n\n..."
}
```

## 5. Skill 定义

### 5.1 CLAUDE.md（编排流程）

定义总流程，Claude Code 启动时的唯一入口：

1. **Phase 1 数据准备**：调用 `fetch-data` → `tech-indicators`
2. **Phase 2 市场状态**：调用 `market-regime`
3. **Phase 3 策略分析**：根据 regime 输出并行调用策略 Agent
4. **Phase 4 决策汇总**：调用 `decision-agent`
5. **Phase 5 呈现**：输出最终 Markdown 报告

### 5.2 数据层 Skill（Python 执行）

- **fetch-data**：运行 `python python/fetch.py --code {code}`，抓取 K 线、实时行情、基本面、新闻写入 JSON
- **tech-indicators**：运行 `python python/indicators.py --code {code}`，计算 MA/MACD/RSI/布林带/乖离率/量能/筹码等写入 JSON

### 5.3 分析层 Skill（Claude Agent 执行）

- **market-regime**：读取 indicators.json → 判断市场状态 → 返回策略推荐列表
- **strategy-xxx**：读取 data/{code}/*.json → 按 YAML 策略规则分析 → 输出 strategy_xxx.json
- **decision-agent**：读所有 strategy_*.json → 加权汇总 → 输出 decision.json + 呈现给用户

### 5.4 策略 Agent 原则

每个策略 Agent 遵循统一的 Skill 模板：
- **角色定义**：你是谁（如"均线金叉策略专家"）
- **输入**：读 data/{code}/ 下各 JSON
- **分析框架**：步骤化分析流程（直接引用 YAML 策略 instructions）
- **输出格式**：统一的 JSON Schema

## 6. 运行流程示例

```
用户: "分析 600519 贵州茅台"

Claude Code:
  ├── /fetch-data 600519           → python fetch.py → data/600519/*.json
  ├── /tech-indicators 600519      → python indicators.py → data/600519/indicators.json
  ├── /market-regime 600519        → Claude 分析 → data/600519/regime.json
  ├── /strategy-ma-golden-cross 600519  → Claude 分析 → data/600519/strategy_ma_golden_cross.json
  ├── /strategy-volume-breakout 600519  → Claude 分析 → data/600519/strategy_volume_breakout.json
  ├── /strategy-bull-trend 600519      → Claude 分析 → data/600519/strategy_bull_trend.json
  └── /decision-agent 600519      → Claude 汇总 → 最终结果呈现给用户
```

## 7. 与原项目的差异

| 维度 | 原项目 | 本方案 |
|------|--------|--------|
| 调度引擎 | Python 线程池 | Claude Code Agent spawn |
| 分析引擎 | LiteLLM 调用外部模型 | Claude 自身分析能力 |
| 策略执行 | Python AgentOrchestrator | Claude Agent Skill |
| Agent 通信 | 共享内存上下文 | JSON 文件 |
| 通知推送 | 10+ 渠道 | 控制台输出 |
| Web UI | React + Vite | 无 |
| Bot | 钉钉/飞书/Discord | 无 |
| 配置方式 | .env 环境变量 | CLAUDE.md + YAML |
| 多股并行 | ThreadPoolExecutor | Claude 并行 spawn |

## 8. 实施顺序

### 模块 1: Python 数据层（Phase 1）
- 从原项目提取 data_provider/
- 创建 python/fetch.py 和 python/indicators.py
- 精简 config.py（剥离 notification 依赖）
- 测试单股数据抓取

### 模块 2: 数据层 Skill（Phase 1）
- 创建 fetch-data Skill
- 创建 tech-indicators Skill

### 模块 3: 市场状态 + 策略 Agent（Phase 2-3）
- 创建 market-regime Skill
- 复制 strategies/ YAML 文件
- 创建首批 3-5 个策略 Agent Skill
- 测试单策略分析链路

### 模块 4: 决策汇总 Agent（Phase 4）
- 创建 decision-agent Skill
- 端到端测试：数据→策略→决策

### 模块 5: 编排 + CLAUDE.md
- 编写 CLAUDE.md 总流程
- 测试完整的多 Agent 链路

### 模块 6: 剩余策略 Agent
- 逐个补齐剩余 10+ 策略
