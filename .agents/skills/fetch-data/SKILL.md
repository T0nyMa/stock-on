---
name: fetch-data
description: 抓取股票行情数据，写入 data/{code}/ 目录。Phase 1 数据准备第一步。
---

# fetch-data

抓取指定股票的行情数据并写入 JSON 文件。

## 用法

`$fetch-data {code}` — 例如 `$fetch-data 600519`

## 执行

运行 Python 数据抓取脚本：

```bash
source .venv/bin/activate && python src/fetch.py --code {code}
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
