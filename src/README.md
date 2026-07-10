# src/ — Python 数据层

数据抓取和技术指标计算。Codex 负责基于已准备数据进行分析，Python 只负责数据准备。

## 入口脚本

| 脚本 | 用法 | 输入 | 输出 |
|------|------|------|------|
| `fetch.py` | `python src/fetch.py --code {code}` | — | data/{code}/kline.json, quote.json, fundamentals.json, news.json |
| `indicators.py` | `python src/indicators.py --code {code}` | data/{code}/kline.json | data/{code}/indicators.json |

## 依赖链

```
fetch.py → config.py → data_provider/ → data/, utils/
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

详见 `data/{code}/` 下各 JSON 文件。Codex 直接读取这些数据文件。
