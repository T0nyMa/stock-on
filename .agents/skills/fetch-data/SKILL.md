---
name: fetch-data
description: 抓取股票行情数据，增量写入 SQLite。Phase 1 数据准备第一步。
---

# fetch-data

抓取指定股票的行情数据并增量写入 SQLite。

## 用法

`$fetch-data {code}` — 例如 `$fetch-data 600519`

## 执行

运行 Python 数据抓取脚本：

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
```

## 输出

数据写入 `data/stock_analysis.db`：

| 数据类型 | 内容 |
|------|------|
| SQLite 日K | 首次默认500个交易日，后续5日重叠增量（OHLCV） |
| `SQLite 行情快照` | 实时行情（价格、涨跌幅、量比、PE/PB、市值） |
| `SQLite 基本面快照` | 基本面（营收、利润、行业） |
| `SQLite 新闻快照` | 近 7 日新闻舆情 |

## 验证

执行完成后运行 `python -m src.data_access --code {code} --kind bars --limit 5`，确认结果不为空。
