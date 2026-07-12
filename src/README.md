# src/ — Python 数据与规范引擎

Python 负责确定性数据抓取、技术指标、量化派生和项目规范校验；Codex 基于已登记证据研究与决策。

## 数据工作流

单股数据准备执行 `python src/fetch.py --code {code}`，指标计算执行 `python src/indicators.py --code {code}`。规范入口分别是 `data-preparation` 和 `quant-analysis`；完整输入、输出及门禁见 `references/generated/workflows.md`。

数据库默认位于 `data/stock_analysis.db`（`database.stock_analysis`）。日 K、行情、基本面、新闻和指标都是 SQLite 中的登记快照，通过下列接口查询：

```bash
python -m src.data_access --code {code} --kind bars|quote|fundamentals|news|indicators
```

运行 `python scripts/run_quant_analysis.py --date YYYY-MM-DD` 从 SQLite 原子数据生成登记的派生上下文 `artifact.report_context`（`data/report_context.json`）。缺失行情、基准、汇率或驱动项会保留 evidence gap / `unavailable`，不得补零。

所有运行时路径、存储类型、新鲜度及缺失行为以 `spec/artifacts.yaml` 为准；文件名不是优先于注册表的隐式契约。

## 规范工具

```bash
python -m src.spec validate
python -m src.spec generate --check
```

`validate` 校验注册表关系，`generate --check` 确认生成参考与注册表一致。
