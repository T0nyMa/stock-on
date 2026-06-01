# 多 Agent 股票分析系统 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 daily_stock_analysis 改造为 Claude Code 驱动的多 Agent 股票分析系统，Python 只做数据抓取和技术指标计算，Claude Agent 负责分析决策。

**Architecture:** Claude Code 作为总调度器，通过 Skill 文件 spawn 子 Agent。Python 层输出 JSON 到 `data/{code}/` 目录，Agent 之间通过 JSON 文件通信（无共享内存）。每个策略对应一个独立 Skill。

**Tech Stack:** Python (data_provider, pandas, numpy), Claude Code Skills (YAML + Markdown)

---

### 模块 0：项目骨架

**说明：** 创建完整的目录结构，为后续所有模块提供基础。

- [ ] **Step 1: 创建目录结构**

```bash
cd /Users/majiang/Work/tools/stock-on
# 清理旧的 clone 目录（避免混淆）
rm -rf daily_stock_analysis

# 创建 python/ 子目录
mkdir -p python/data_provider
mkdir -p python/data
mkdir -p python/utils
mkdir -p python/llm

# 创建 data/ 目录
mkdir -p data

# 创建 strategies/ 目录
mkdir -p strategies

# 创建 skills 目录
mkdir -p .claude/skills

# 创建文档目录
mkdir -p docs
```

---

### 模块 1：Python 数据层（从原项目提取）

**说明：** 从 daily_stock_analysis 项目中提取数据源和技术分析模块，去掉通知/webui/bot 依赖。

注意：由于我们 clone 后 review 完了，可以把该项目删掉重新 clone，或者直接从 clone 的目录复制文件。为了方便，直接克隆到临时目录再复制。

- [ ] **Task 1.1: 重新克隆原项目并复制 data_provider**

```bash
cd /tmp
rm -rf daily_stock_analysis
git clone --depth 1 https://github.com/ZhuLinsen/daily_stock_analysis.git
# 复制 data_provider
cp -r /tmp/daily_stock_analysis/data_provider/* /Users/majiang/Work/tools/stock-on/python/data_provider/
# 复制 stock_analyzer.py
cp /tmp/daily_stock_analysis/src/stock_analyzer.py /Users/majiang/Work/tools/stock-on/python/stock_analyzer.py
# 复制 src/data/
cp -r /tmp/daily_stock_analysis/src/data/* /Users/majiang/Work/tools/stock-on/python/data/
# 复制 src/utils/
cp /tmp/daily_stock_analysis/src/utils/sanitize.py /Users/majiang/Work/tools/stock-on/python/utils/sanitize.py
cp /tmp/daily_stock_analysis/src/utils/data_processing.py /Users/majiang/Work/tools/stock-on/python/utils/data_processing.py
# 复制 src/enums.py
cp /tmp/daily_stock_analysis/src/enums.py /Users/majiang/Work/tools/stock-on/python/enums.py
# 复制 src/report_language.py
cp /tmp/daily_stock_analysis/src/report_language.py /Users/majiang/Work/tools/stock-on/python/report_language.py
# 复制 src/llm/ (仅 generation_params.py)
cp /tmp/daily_stock_analysis/src/llm/generation_params.py /Users/majiang/Work/tools/stock-on/python/llm/generation_params.py
# 复制 src/services/run_diagnostics.py
cp /tmp/daily_stock_analysis/src/services/run_diagnostics.py /Users/majiang/Work/tools/stock-on/python/utils/run_diagnostics.py
# 复制 src/logging_config.py
cp /tmp/daily_stock_analysis/src/logging_config.py /Users/majiang/Work/tools/stock-on/python/logging_config.py
# 复制 strategies/
cp /tmp/daily_stock_analysis/strategies/* /Users/majiang/Work/tools/stock-on/strategies/
```

- [ ] **Task 1.2: 创建精简版 config.py**

创建 `python/config.py`，剥离通知/webui/bot 相关依赖。这是原项目 `src/config.py` 的精简版本。

```python
"""
Stock-On: 精简配置管理模块
从原 daily_stock_analysis 提取，去掉 notification/webui/bot 依赖。
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from dotenv import load_dotenv, dotenv_values
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """统一配置类，从环境变量加载"""
    # === 股票列表 ===
    stock_list: List[str] = field(default_factory=list)

    # === 数据源配置 ===
    tushare_token: Optional[str] = None
    use_proxy: bool = False
    proxy_host: str = "127.0.0.1"
    proxy_port: str = "10809"

    # === 分析配置 ===
    debug: bool = False
    dry_run: bool = False
    log_dir: str = "logs"
    log_level: str = "INFO"
    report_language: str = "zh"
    max_workers: int = 4
    analysis_delay: int = 0
    data_dir: str = "data"

    # === 交易日检查 ===
    trading_day_check_enabled: bool = True

    def validate(self) -> List[str]:
        warnings = []
        if not self.stock_list:
            warnings.append("STOCK_LIST 为空，请配置自选股代码")
        return warnings

    def refresh_stock_list(self):
        """从环境变量刷新股票列表"""
        raw = os.getenv("STOCK_LIST", "")
        self.stock_list = [s.strip() for s in raw.split(",") if s.strip()]


def setup_env():
    """加载 .env 文件"""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)
        logger.info("已加载 .env 配置文件")


def get_config() -> Config:
    """获取配置实例（单例）"""
    cfg = Config()
    raw = os.getenv("STOCK_LIST", "")
    cfg.stock_list = [s.strip() for s in raw.split(",") if s.strip()]
    cfg.tushare_token = os.getenv("TUSHARE_TOKEN")
    cfg.debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
    cfg.log_dir = os.getenv("LOG_DIR", "logs")
    cfg.log_level = os.getenv("LOG_LEVEL", "INFO")
    cfg.data_dir = os.getenv("DATA_DIR", "data")
    cfg.use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"
    cfg.proxy_host = os.getenv("PROXY_HOST", "127.0.0.1")
    cfg.proxy_port = os.getenv("PROXY_PORT", "10809")
    cfg.trading_day_check_enabled = os.getenv("TRADING_DAY_CHECK_ENABLED", "true").lower() != "false"
    cfg.max_workers = int(os.getenv("MAX_WORKERS", "4"))
    return cfg
```

- [ ] **Task 1.3: 创建 python/data/__init__.py**

创建空的包初始化文件：
```python
# data package
```

- [ ] **Task 1.4: 创建 python/utils/__init__.py**

```python
# utils package
```

- [ ] **Task 1.5: 创建 python/llm/__init__.py**

```python
# llm package
```

- [ ] **Task 1.6: 修复 python/data_provider/base.py 的 import 路径**

原代码用 `from src.xxx import ...`，需要改为 `from python.xxx import ...` 或相对导入。

编辑 `python/data_provider/base.py`：

```python
# 修改第27-29行
# 原：from src.data.stock_index_loader import get_index_stock_name
# 改：from python.data.stock_index_loader import get_index_stock_name
from python.data.stock_index_loader import get_index_stock_name
from python.data.stock_mapping import STOCK_NAME_MAP, is_meaningful_stock_name
from python.utils.run_diagnostics import record_provider_run
```

- [ ] **Task 1.7: 修复 data_provider 各 fetcher 的 import 路径**

检查并修复所有 fetcher 中的 `from src.xxx` 和 `from data_provider.xxx` 导入。

编辑 `python/data_provider/akshare_fetcher.py`，将 `from data_provider.xxx` 改为 `from python.data_provider.xxx`：
```python
# 搜索替换：from data_provider. → from python.data_provider.
# 搜索替换：from src. → from python.
```

对所有 fetcher 文件执行相同的 import 修复：
```bash
cd /Users/majiang/Work/tools/stock-on/python
# 修复 data_provider 中的 import
for f in data_provider/*.py; do
    sed -i '' 's/from src\./from python./g' "$f"
    sed -i '' 's/from data_provider\./from python.data_provider./g' "$f"
done
# 修复顶级模块中的 import
for f in *.py utils/*.py data/*.py llm/*.py; do
    if [ -f "$f" ]; then
        sed -i '' 's/from src\./from python./g' "$f"
        sed -i '' 's/from data_provider\./from python.data_provider./g' "$f"
    fi
done
```

- [ ] **Task 1.8: 创建 python/fetch.py**

```python
#!/usr/bin/env python3
"""
数据抓取入口。供 Claude Code fetch-data Skill 调用。

用法: python python/fetch.py --code 600519
输出: data/{code}/kline.json, quote.json, fundamentals.json, news.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# 确保 python/ 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from python.config import get_config, setup_env
from python.data_provider import DataFetcherManager
from python.data_provider.base import canonical_stock_code

logger = logging.getLogger(__name__)


def _ensure_data_dir(code: str) -> Path:
    config = get_config()
    data_dir = Path(config.data_dir)
    stock_dir = data_dir / code
    stock_dir.mkdir(parents=True, exist_ok=True)
    return stock_dir


def _write_json(stock_dir: Path, filename: str, data: dict):
    path = stock_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("已写入: %s", path)


def fetch_stock_data(code: str):
    """抓取单只股票的完整数据"""
    setup_env()
    config = get_config()
    stock_dir = _ensure_data_dir(code)

    fetcher = DataFetcherManager(config)

    # 1. 抓取 K 线（近 60 个交易日）
    logger.info("正在获取 %s K线数据...", code)
    try:
        kline = fetcher.get_daily_history(code, count=60)
        if kline is not None and not kline.empty:
            records = kline.to_dict(orient="records")
            _write_json(stock_dir, "kline.json", {
                "code": code,
                "name": fetcher.get_stock_name(code),
                "market": _detect_market(code),
                "updated_at": _now_str(),
                "kline": _convert_dates(records),
            })
        else:
            logger.warning("K线数据为空: %s", code)
    except Exception as e:
        logger.error("获取K线失败 %s: %s", code, e)

    # 2. 抓取实时行情
    logger.info("正在获取 %s 实时行情...", code)
    try:
        quote = fetcher.get_realtime_quote(code)
        if quote:
            _write_json(stock_dir, "quote.json", {
                "code": code,
                "name": getattr(quote, "name", ""),
                "price": getattr(quote, "price", 0),
                "pct_chg": getattr(quote, "pct_chg", 0),
                "volume": getattr(quote, "volume", 0),
                "amount": getattr(quote, "amount", 0),
                "turnover_rate": getattr(quote, "turnover_rate", 0),
                "pe": getattr(quote, "pe", 0),
                "pb": getattr(quote, "pb", 0),
                "market_cap": getattr(quote, "market_cap", 0),
                "updated_at": _now_str(),
            })
    except Exception as e:
        logger.error("获取行情失败 %s: %s", code, e)

    # 3. 抓取基本面
    logger.info("正在获取 %s 基本面...", code)
    try:
        fundamentals = fetcher.get_fundamentals(code)
        if fundamentals:
            _write_json(stock_dir, "fundamentals.json", {
                "code": code,
                "name": fundamentals.get("name", ""),
                "pe": fundamentals.get("pe"),
                "pb": fundamentals.get("pb"),
                "market_cap": fundamentals.get("market_cap"),
                "revenue": fundamentals.get("revenue"),
                "profit": fundamentals.get("profit"),
                "industry": fundamentals.get("industry"),
                "updated_at": _now_str(),
            })
    except Exception as e:
        logger.warning("获取基本面失败 %s: %s", code, e)

    # 4. 抓取新闻
    logger.info("正在获取 %s 新闻...", code)
    try:
        from python.search_service import SearchService
        search = SearchService(config)
        news = search.search_stock_news(code, days=7)
        if news:
            _write_json(stock_dir, "news.json", {
                "code": code,
                "news": news,
                "updated_at": _now_str(),
            })
    except Exception as e:
        logger.warning("获取新闻失败 %s: %s", code, e)

    logger.info("数据抓取完成: %s → %s", code, stock_dir)


def _detect_market(code: str) -> str:
    code = code.upper()
    if code.startswith("HK"):
        return "HK"
    if code.startswith(("US", "NYSE", "NASDAQ")):
        return "US"
    if code.startswith(("6", "5")):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("4", "8")):
        return "BJ"
    return ""


def _now_str() -> str:
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat()


def _convert_dates(records: list) -> list:
    """Convert pandas Timestamps to ISO strings for JSON serialization."""
    import pandas as pd
    for r in records:
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                r[k] = v.isoformat()
    return records


def main():
    parser = argparse.ArgumentParser(description="股票数据抓取")
    parser.add_argument("--code", required=True, help="股票代码")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    code = canonical_stock_code(args.code)
    fetch_stock_data(code)


if __name__ == "__main__":
    main()
```

- [ ] **Task 1.9: 创建 python/indicators.py**

```python
#!/usr/bin/env python3
"""
技术指标计算入口。供 Claude Code tech-indicators Skill 调用。

用法: python python/indicators.py --code 600519
输入: data/{code}/kline.json
输出: data/{code}/indicators.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from python.config import get_config
from python.stock_analyzer import StockTrendAnalyzer

logger = logging.getLogger(__name__)


def compute_indicators(code: str):
    """计算技术指标并写入 JSON"""
    config = get_config()
    data_dir = Path(config.data_dir)
    stock_dir = data_dir / code
    kline_path = stock_dir / "kline.json"

    if not kline_path.exists():
        logger.error("K线数据不存在: %s", kline_path)
        return False

    with open(kline_path, "r", encoding="utf-8") as f:
        kline_data = json.load(f)

    import pandas as pd
    df = pd.DataFrame(kline_data["kline"])
    if df.empty:
        logger.error("K线为空: %s", code)
        return False

    # 确保日期排序
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # 使用 StockTrendAnalyzer 计算技术指标
    analyzer = StockTrendAnalyzer()
    result = analyzer.analyze(df)

    indicators = {
        "code": code,
        "updated_at": kline_data.get("updated_at", ""),
        "ma": {
            "ma5": _safe_float(getattr(result, "ma5", None)),
            "ma10": _safe_float(getattr(result, "ma10", None)),
            "ma20": _safe_float(getattr(result, "ma20", None)),
            "ma60": _safe_float(getattr(result, "ma60", None)),
        },
        "macd": {
            "dif": _safe_float(getattr(result, "macd_dif", None)),
            "dea": _safe_float(getattr(result, "macd_dea", None)),
            "hist": _safe_float(getattr(result, "macd_hist", None)),
        },
        "rsi": {
            "rsi6": _safe_float(getattr(result, "rsi6", None)),
            "rsi12": _safe_float(getattr(result, "rsi12", None)),
            "rsi24": _safe_float(getattr(result, "rsi24", None)),
        },
        "volume": {
            "ma5_vol": _safe_float(getattr(result, "ma5_volume", None)),
            "volume_ratio": _safe_float(getattr(result, "volume_ratio", None)),
        },
        "boll": {
            "upper": _safe_float(getattr(result, "boll_upper", None)),
            "mid": _safe_float(getattr(result, "boll_mid", None)),
            "lower": _safe_float(getattr(result, "boll_lower", None)),
        },
        "bias": {
            "bias5": _safe_float(getattr(result, "bias5", None)),
            "bias10": _safe_float(getattr(result, "bias10", None)),
            "bias20": _safe_float(getattr(result, "bias20", None)),
        },
        "chip": {
            "concentration": _safe_float(getattr(result, "chip_concentration", None)),
            "profit_ratio": _safe_float(getattr(result, "profit_ratio", None)),
            "avg_cost": _safe_float(getattr(result, "avg_cost", None)),
        },
        "trend": {
            "status": getattr(result, "trend_status", ""),
            "ma_alignment": _describe_ma_alignment(result),
            "support_levels": _safe_list(getattr(result, "support_levels", [])),
            "resistance_levels": _safe_list(getattr(result, "resistance_levels", [])),
        },
    }

    output_path = stock_dir / "indicators.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(indicators, f, ensure_ascii=False, indent=2, default=str)
    logger.info("技术指标已写入: %s", output_path)
    return True


def _safe_float(val):
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return None


def _safe_list(val):
    if val is None:
        return []
    return [round(float(v), 2) if v else 0 for v in val]


def _describe_ma_alignment(result) -> str:
    ma5 = getattr(result, "ma5", None)
    ma10 = getattr(result, "ma10", None)
    ma20 = getattr(result, "ma20", None)
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            return "MA5>MA10>MA20"
        if ma5 < ma10 < ma20:
            return "MA5<MA10<MA20"
        if ma5 > ma10 and ma10 < ma20:
            return "MA5>MA10<MA20"
        if ma5 < ma10 and ma10 > ma20:
            return "MA5<MA10>MA20"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description="技术指标计算")
    parser.add_argument("--code", required=True, help="股票代码")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    compute_indicators(args.code)


if __name__ == "__main__":
    main()
```

- [ ] **Task 1.10: 安装依赖 & 验证数据层**

```bash
cd /Users/majiang/Work/tools/stock-on
pip install python-dotenv pandas numpy akshare efinance yfinance

# 配置测试用股票
echo 'STOCK_LIST=600519,000001' > .env

# 测试数据抓取
python python/fetch.py --code 600519
# 预期输出：K线数据已写入 data/600519/kline.json

# 测试技术指标计算
python python/indicators.py --code 600519
# 预期输出：技术指标已写入 data/600519/indicators.json

# 验证 JSON 输出
ls -la data/600519/
```

---

### 模块 2：数据层 Skills

- [ ] **Task 2.1: 创建 fetch-data Skill**

创建 `.claude/skills/fetch-data/SKILL.md`：

```markdown
---
name: fetch-data
description: 抓取股票行情数据，写入 data/{code}/ 目录。Phase 1 数据准备第一步。
---

# fetch-data

抓取指定股票的行情数据并写入 JSON 文件。

## 用法

`/fetch-data {code}` — 例如 `/fetch-data 600519`

## 执行

运行 Python 数据抓取脚本：

```bash
python python/fetch.py --code {code}
```

## 输出

数据写入到 `data/{code}/` 目录：

| 文件 | 内容 |
|------|------|
| `kline.json` | 近 60 个交易日 K 线（OHLCV） |
| `quote.json` | 实时行情（价格、涨跌幅、量比、PE/PB、市值） |
| `fundamentals.json` | 基本面（营收、利润、行业） |
| `news.json` | 近 7 日新闻舆情 |

## 验证

执行完成后确认 `data/{code}/kline.json` 存在且不为空。

用 `cat data/{code}/kline.json` 查看数据概览。
```

- [ ] **Task 2.2: 创建 tech-indicators Skill**

创建 `.claude/skills/tech-indicators/SKILL.md`：

```markdown
---
name: tech-indicators
description: 计算股票技术指标，写入 data/{code}/indicators.json。Phase 1 数据准备第二步。
---

# tech-indicators

基于 K 线数据计算技术指标。

## 用法

`/tech-indicators {code}` — 例如 `/tech-indicators 600519`

前置条件：`/fetch-data {code}` 必须先执行。

## 执行

```bash
python python/indicators.py --code {code}
```

## 输出

写入 `data/{code}/indicators.json`，包含：

| 指标组 | 字段 |
|--------|------|
| 均线系统 | ma5, ma10, ma20, ma60 |
| MACD | dif, dea, hist |
| RSI | rsi6, rsi12, rsi24 |
| 布林带 | upper, mid, lower |
| 乖离率 | bias5, bias10, bias20 |
| 量能 | ma5_vol, volume_ratio |
| 筹码结构 | concentration, profit_ratio, avg_cost |
| 趋势判断 | status, ma_alignment, support_levels, resistance_levels |

## 验证

确认 `data/{code}/indicators.json` 存在且包含完整指标。
用 `cat data/{code}/indicators.json` 查看数据。
```

---

### 模块 3：市场状态 + 策略 Agent Skills（首批 5 个）

- [ ] **Task 3.1: 创建 market-regime Skill**

创建 `.claude/skills/market-regime/SKILL.md`：

```markdown
---
name: market-regime
description: 读取技术指标，判断市场状态，推荐分析策略。Phase 2。
---

# market-regime

市场状态识别 Agent。根据技术指标判断当前市场处于什么状态，推荐最匹配的分析策略。

## 用法

`/market-regime {code}` — 例如 `/market-regime 600519`

前置条件：`/tech-indicators {code}` 必须先执行。

## 输入

读取 `data/{code}/indicators.json`

## 分析方法

依次检查以下市场状态：

### 1. trending_up（多头趋势）
- MA5 > MA10 > MA20 多头排列
- MACD 在零轴上方或金叉
- 价格在布林带中轨上方运行
- **匹配策略**：均线金叉、放量突破、多头趋势、缩量回调、龙头股

### 2. volatile（震荡盘整）
- 均线缠绕，无明显方向
- 价格在布林带上下轨之间反复
- MACD 在零轴附近反复交叉
- **匹配策略**：缠论、箱体震荡、波浪理论、地量、一阳三阴

### 3. sector_hot（热点题材）
- 板块联动明显，个股与板块共振
- 成交量放大
- **匹配策略**：热点题材、事件驱动、情绪周期、龙头股

### 4. bearish（空头趋势）
- MA5 < MA10 < MA20 空头排列
- 价格在布林带中轨下方运行
- **匹配策略**：预期重估、成长质量、事件驱动

## 输出

写入 `data/{code}/regime.json`：

```json
{
  "regime": "trending_up",
  "confidence": 0.85,
  "reasoning": "MA5>MA10>MA20 多头排列，MACD 零轴上方运行",
  "recommended_strategies": [
    {"name": "ma_golden_cross", "priority": 20, "reason": "..."},
    {"name": "volume_breakout", "priority": 30, "reason": "..."}
  ]
}
```

使用 Write 工具写入该 JSON 文件。
```

- [ ] **Task 3.2: 创建 strategy-ma-golden-cross Skill**

创建 `.claude/skills/strategy-ma-golden-cross/SKILL.md`：

```markdown
---
name: strategy-ma-golden-cross
description: 均线金叉策略 — MA5 上穿 MA10/MA20 的量价配合信号判断。
---

# 均线金叉策略 Agent

你是均线金叉策略专家，精通经典均线系统的买卖点判断。

## 用法

`/strategy-ma-golden-cross {code}` — 例如 `/strategy-ma-golden-cross 600519`

## 输入

读取 `data/{code}/` 下所有 JSON 数据：
- `kline.json` — 近 60 日 K 线
- `quote.json` — 实时行情
- `indicators.json` — 技术指标
- `news.json` — 新闻舆情

用 Read 工具逐一读取。

## 分析框架

严格按以下步骤执行：

### Step 1: 金叉检测
- MA5 是否在最近 3 个交易日内上穿 MA10？
- MA10 是否上穿 MA20？（更慢但更可靠）
- MACD 是否金叉或零轴上方金叉？
- 读取 indicators.json 中的 `ma` 和 `macd` 字段

### Step 2: 量能确认
- 金叉日成交量 > 5 日均量？
- 量比 > 1.2 为积极信号
- 检查 indicators.json 中的 `volume` 字段

### Step 3: 趋势背景判断
- 盘整后金叉 → 最强信号
- 上升趋势中金叉 → 延续信号
- 深度下跌中金叉 → 弱信号，需更多确认
- 检查 indicators.json 中的 `trend` 字段

### Step 4: 价格位置检查
- 价格在交叉均线附近或上方？
- 乖离率 < 5%（不追高）
- 检查 indicators.json 中的 `bias` 字段

### Step 5: 风险评估
- 检查 news.json 有无重大利空
- 检查筹码结构（集中度、获利比例）
- 读取 quote.json 中的 PE/PB

## 输出

使用 Write 工具写入 `data/{code}/strategy_ma_golden_cross.json`：

```json
{
  "strategy": "ma_golden_cross",
  "display_name": "均线金叉",
  "stock_code": "600519",
  "signal": "buy|hold|sell",
  "score": 75,
  "confidence": 0.8,
  "reasoning": "2-3 句话概括判断逻辑",
  "key_levels": {
    "support": 1790.0,
    "resistance": 1820.0,
    "entry": 1805.0,
    "stop_loss": 1760.0
  },
  "risk_flags": ["风险1", "风险2"],
  "details": "详细分析文本（支持 Markdown）"
}
```
```

- [ ] **Task 3.3: 创建 strategy-volume-breakout Skill**

创建 `.claude/skills/strategy-volume-breakout/SKILL.md`：

```markdown
---
name: strategy-volume-breakout
description: 放量突破策略 — 检测股价放量突破阻力位信号。
---

# 放量突破策略 Agent

你是放量突破策略专家，精通量价突破判断。

## 用法

`/strategy-volume-breakout {code}`

## 输入

同均线金叉：读 `data/{code}/` 下 kline.json, quote.json, indicators.json, news.json

## 分析框架

### Step 1: 阻力位识别
- 从 indicators.json 中读取 `trend.resistance_levels`
- 识别 20 日高点或前期震荡平台顶部

### Step 2: 量能确认
- 当日成交量 > 5 日均量的 2 倍？
- 量比 > 2.0？
- 检查 indicators.json 的 `volume` 字段和 quote.json

### Step 3: 价格确认
- 收盘价站上阻力位
- 突破后乖离率 < 5%（不追高）

### Step 4: 风险过滤
- 搜索 news.json 有无重大利空
- PE 过高则提示泡沫风险

## 输出

写入 `data/{code}/strategy_volume_breakout.json`，格式同上。
```

- [ ] **Task 3.4: 创建 strategy-bull-trend Skill**

创建 `.claude/skills/strategy-bull-trend/SKILL.md`：

```markdown
---
name: strategy-bull-trend
description: 多头趋势策略 — 判断股票是否处于强势多头趋势。
---

# 多头趋势策略 Agent

你是多头趋势策略专家，擅长识别强势上升趋势。

## 用法

`/strategy-bull-trend {code}`

## 输入

读 `data/{code}/` 下 kline.json, indicators.json, quote.json

## 分析框架

### Step 1: 多头排列检查
- MA5 > MA10 > MA20，且间距在扩大（发散上行）
- 价格沿 MA5 上行，不破 MA10
- indicators.json 中 `trend.ma_alignment` 验证

### Step 2: 强势特征
- 连续 3 日涨幅 > 0 或阳线多于阴线
- 回调缩量、上涨放量
- 从 kline.json 逐日检查

### Step 3: 乖离率风险
- bias5 < 5% 可持有
- bias5 > 8% 提示短期过热风险

### Step 4: 支撑位确认
- MA10 为第一支撑
- MA20 为第二支撑（跌破则趋势可能反转）

## 输出

写入 `data/{code}/strategy_bull_trend.json`
```

- [ ] **Task 3.5: 创建 strategy-chan-theory Skill**

创建 `.claude/skills/strategy-chan-theory/SKILL.md`：

```markdown
---
name: strategy-chan-theory
description: 缠论策略 — 基于缠论笔、线段、中枢结构分析。
---

# 缠论策略 Agent

你是缠论分析专家，精通分型、笔、线段、中枢、背驰和买卖点判断。

## 用法

`/strategy-chan-theory {code}`

## 输入

读 `data/{code}/` 下 kline.json, indicators.json

## 分析框架

### Step 1: 分型识别
- 从 kline.json 中找顶分型和底分型
- 顶分型：中间 K 线最高价 > 左右 K 线最高价
- 底分型：中间 K 线最低价 < 左右 K 线最低价

### Step 2: 笔 + 线段
- 连接相邻的底分型和顶分型形成"笔"
- 3 笔重叠形成"线段"

### Step 3: 中枢识别
- 连续 3 段走势重叠区间构成中枢
- 判断当前价格在中枢内还是已脱离

### Step 4: 背驰判断
- **顶背驰**：价格创新高但 MACD 面积缩小 → 卖出信号
- **底背驰**：价格创新低但 MACD 面积缩小 → 买入信号
- 从 indicators.json 读取 macd 数据，与原价格对比

### Step 5: 买卖点判定
- **一买**：下跌趋势 + 底背驰
- **二买**：回调不破中枢高点
- **三买**：突破中枢后回调不进中枢

## 输出

写入 `data/{code}/strategy_chan_theory.json`
```

- [ ] **Task 3.6: 创建 strategy-hot-theme Skill**

创建 `.claude/skills/strategy-hot-theme/SKILL.md`：

```markdown
---
name: strategy-hot-theme
description: 热点题材策略 — 判断个股是否受益于当前市场热点。
---

# 热点题材策略 Agent

你是热点题材分析专家，擅长判断题材强度和个股相关性。

## 用法

`/strategy-hot-theme {code}`

## 输入

读 `data/{code}/` 下 quote.json, news.json, indicators.json

## 分析框架

### Step 1: 热点识别
- 从 news.json 中提取政策、产业、技术热点关键词
- 判断个股业务与热点的相关性：实质受益 / 间接受益 / 概念蹭热点

### Step 2: 相对强弱
- 检查涨幅、量比、换手率是否异常
- 对比同板块其他个股（如果有数据）

### Step 3: 节奏判断
- 热点处于：启动 / 扩散 / 分化 / 退潮 哪个阶段？
- 基于新闻时间和价格走势综合判断

### Step 4: 风险检查
- 乖离率是否过大？
- 新闻是否集中在"已经大涨"?"资金追捧"？
- 有无监管问询或澄清公告？

## 输出

写入 `data/{code}/strategy_hot_theme.json`
```

---

### 模块 4：决策汇总 Agent

- [ ] **Task 4.1: 创建 decision-agent Skill**

创建 `.claude/skills/decision-agent/SKILL.md`：

```markdown
---
name: decision-agent
description: 决策汇总 Agent — 收集所有策略输出，生成最终决策仪表盘。
---

# 决策汇总 Agent

你是决策汇总专家。你的任务是将多个策略 Agent 的分析结果汇总为一份清晰的决策仪表盘。

## 用法

`/decision-agent {code}` — 例如 `/decision-agent 600519`

前置条件：至少一个 strategy-xxx Skill 已完成分析。

## 输入

用 Read 工具读取 `data/{code}/` 下所有 `strategy_*.json` 文件，以及 `regime.json`。

## 汇总方法

### 1. 加权评分

根据各策略得分和置信度计算加权总分：

```
总评分 = Σ(score_i × confidence_i × weight_i) / Σ(confidence_i × weight_i)
```

| 策略类型 | 默认权重 |
|---------|---------|
| 趋势类（均线金叉、多头趋势） | 1.0 |
| 形态类（缠论、箱体震荡） | 0.9 |
| 量价类（放量突破、缩量回调） | 1.0 |
| 题材类（热点题材、事件驱动） | 0.8 |

### 2. 信号综合

- 多数策略看多 → overall_signal = "buy"
- 多数策略看空 → overall_signal = "sell"
- 信号分歧 → overall_signal = "hold"

### 3. 风险汇总

- 收集所有策略的 risk_flags
- 去重后按严重程度排序输出

### 4. 关键价位

- 从各策略的 key_levels 中取 support/entry/stop_loss 的中位数

## 输出

用 Write 工具写入 `data/{code}/decision.json`：

```json
{
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "overall_signal": "buy|hold|sell",
  "overall_score": 72,
  "strategies_used": ["ma_golden_cross", "volume_breakout", "bull_trend"],
  "weighted_scores": {
    "ma_golden_cross": 75,
    "volume_breakout": 68
  },
  "key_levels": {
    "support": 1790,
    "resistance": 1830,
    "entry": 1800,
    "stop_loss": 1760
  },
  "risk_flags": ["风险1", "风险2"],
  "catalysts": ["利好1", "利好2"],
  "final_report": "## 决策仪表盘\n\n..."
}
```

## 呈现给用户

在 `final_report` 中生成 Markdown 格式的决策仪表盘，包含：
1. **核心结论**：一句话（评分 + 信号）
2. **策略汇总表**：各策略打分一览
3. **关键价位**：支撑/阻力/入场/止损
4. **风险警报**：标红显示
5. **操作建议**：具体的操作检查清单
```

---

### 模块 5：编排 + CLAUDE.md

- [ ] **Task 5.1: 创建 CLAUDE.md**

创建项目根目录的 `CLAUDE.md`：

```markdown
# Stock-On: Claude Code 驱动的多 Agent 股票分析系统

## 项目简介

基于 Claude Code 多 Agent 架构的股票分析系统。**Python 只负责数据抓取和技术指标计算，Claude Agent 负责所有分析决策。** 
Agent 之间通过 `data/{code}/` 下的 JSON 文件通信。

## 目录结构

```
python/           # Python 数据处理层（数据抓取 + 技术指标）
strategies/       # YAML 策略定义
data/{code}/      # 数据落地 + Agent 间通信
.claude/skills/   # Claude Code Skill 定义
```

## 核心流程

当你收到 "分析 {股票代码}" 的指令时，按以下顺序执行：

### Phase 1: 数据准备
1. 调用 `/fetch-data {code}` — 抓取行情数据到 `data/{code}/`
2. 调用 `/tech-indicators {code}` — 计算技术指标到 `data/{code}/indicators.json`

### Phase 2: 市场状态识别
3. 调用 `/market-regime {code}` — 判断市场状态 → 匹配策略 → 写入 `data/{code}/regime.json`

### Phase 3: 并行策略分析
4. 读取 `data/{code}/regime.json` 中的 `recommended_strategies` 列表
5. 取前 3-5 个策略，同时 spawn Agent 执行：
   - `/strategy-{name} {code}` → 读数据 → Claude 分析 → 输出 `data/{code}/strategy_{name}.json`

### Phase 4: 决策汇总
6. 调用 `/decision-agent {code}` → 读所有策略输出 → 生成最终决策仪表盘

### Phase 5: 呈现
7. 将 `decision.json` 中的 `final_report` 呈现给用户

## 多股票分析

如果需要分析多只股票，每只独立执行 Phase 1-4。

## 可选：直接调用单策略

用户也可以直接指定单个策略：
- `/strategy-ma-golden-cross 600519` — 仅用均线金叉分析
- `/strategy-chan-theory 000001` — 仅用缠论分析
```

---

### 模块 6：剩余策略 Agent（10 个）

以下策略按同一模板创建，每个对应一个 Skill 文件。分析框架从对应 YAML 文件提取核心规则。

**通用模板**（每个 Skill 文件）：

```markdown
---
name: strategy-{name}
description: {display_name}策略 — {description}
---

# {display_name}策略 Agent

你是个策略专家，分析框架如下。

## 用法

`/strategy-{name} {code}`

## 输入

读 `data/{code}/` 下 kline.json, indicators.json, quote.json, news.json

## 分析框架

### Step 1: [规则1]
### Step 2: [规则2]
### Step 3: [规则3]
### Step 4: 风险评估

## 输出

写入 `data/{code}/strategy_{name}.json`，格式见均线金叉策略。
```

- [ ] **Task 6.1: strategy-shrink-pullback — 缩量回调策略**

YAML: `strategies/shrink_pullback.yaml`
核心规则：缩量回踩 MA5/MA10 支撑，量缩价稳，等待反弹。

- [ ] **Task 6.2: strategy-dragon-head — 龙头股策略**

YAML: `strategies/dragon_head.yaml`
核心规则：板块龙头、放量突破、强于板块、高辨识度。

- [ ] **Task 6.3: strategy-box-oscillation — 箱体震荡策略**

YAML: `strategies/box_oscillation.yaml`
核心规则：箱体上下轨识别、突破/跌破判断、震荡区间交易。

- [ ] **Task 6.4: strategy-growth-quality — 成长质量策略**

YAML: `strategies/growth_quality.yaml`
核心规则：营收增长、利润增长、ROE、现金流质量。

- [ ] **Task 6.5: strategy-event-driven — 事件驱动策略**

YAML: `strategies/event_driven.yaml`
核心规则：业绩公告、股权变动、重大合同、政策利好。

- [ ] **Task 6.6: strategy-emotion-cycle — 情绪周期策略**

YAML: `strategies/emotion_cycle.yaml`
核心规则：市场情绪阶段（冰点→启动→高潮→退潮）、换手率、涨停跌停。

- [ ] **Task 6.7: strategy-expectation-repricing — 预期重估策略**

YAML: `strategies/expectation_repricing.yaml`
核心规则：PE/PB 历史分位、业绩拐点、行业周期反转。

- [ ] **Task 6.8: strategy-wave-theory — 波浪理论策略**

YAML: `strategies/wave_theory.yaml`
核心规则：5 浪上涨 / 3 浪下跌、浪型识别、斐波那契目标位。

- [ ] **Task 6.9: strategy-bottom-volume — 地量策略**

YAML: `strategies/bottom_volume.yaml`
核心规则：成交量缩至阶段地量、价格企稳、变盘信号。

- [ ] **Task 6.10: strategy-one-yang-three-yin — 一阳三阴策略**

YAML: `strategies/one_yang_three_yin.yaml`
核心规则：一阳穿三阴、阳线反包、底部反转形态。

---

## 验证方式

### 端到端单股测试

```bash
# 1. 数据抓取
python python/fetch.py --code 600519

# 2. 技术指标
python python/indicators.py --code 600519

# 3. 验证 JSON 完整性
python -c "
import json
files = ['kline.json', 'quote.json', 'indicators.json']
for f in files:
    path = f'data/600519/{f}'
    with open(path) as fh:
        data = json.load(fh)
    print(f'{f}: {len(json.dumps(data))} bytes OK')
"

# 4. 在 Claude Code 中测试多 Agent 链路：
# /market-regime 600519
# /strategy-ma-golden-cross 600519
# /strategy-volume-breakout 600519
# /decision-agent 600519
```
