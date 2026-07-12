# src/ — Python 数据层

数据抓取和技术指标计算。Codex 负责基于已准备数据进行分析，Python 只负责数据准备。

## 入口脚本

| 脚本 | 用法 | 输入 | 输出 |
|------|------|------|------|
| `fetch.py` | `python src/fetch.py --code {code}` | — | SQLite 日K（`python -m src.data_access --code {code} --kind bars`）, SQLite 行情快照, SQLite 基本面快照, SQLite 新闻快照 |
| `indicators.py` | `python src/indicators.py --code {code}` | SQLite 日K（`python -m src.data_access --code {code} --kind bars`） | SQLite 指标快照（`python -m src.data_access --code {code} --kind indicators`） |

## 依赖链

```
fetch.py → config.py → data_provider/ → SQLite, utils/
                    → search_service.py (新闻，国内网络可能不可用)

indicators.py → config.py → stock_analyzer.py → enums.py
```

## 数据源

- **K线**: TickFlow API（免费层级）
- **实时行情**: 腾讯财经（通过 akshare）
- **基本面**: 各数据源综合
- **新闻**: SearXNG（国内网络不可用）

## 环境

```bash
source .venv/bin/activate
python src/fetch.py --code 002050
python src/indicators.py --code 002050
```

## 输出格式

运行 `python scripts/run_quant_analysis.py --date YYYY-MM-DD` 可从 SQLite 日K原子生成 schema version `2.0` 的量化 artifacts 与 `data/report_context.json`。该步骤不联网；缺失行情、benchmark、FX 或 driver 会记录 evidence gap，不会填零。

数据库默认位于 `data/stock_analysis.db`。Codex 使用 `python -m src.data_access --code {code} --kind bars|quote|fundamentals|news|indicators` 查询。
