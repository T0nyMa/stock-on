# 研究资料包契约

每次财报深研建立 `tracking/{code}-{name}/research/{date}/`，并将事实采集与分析报告分离。

## 必需目录

`official/`、`earnings-calls/`、`estimates/`、`media/`、`regulatory/`、`peers/`、`tables/`，以及根目录的 `index.md` 和 `claims.json`。

`index.md` 每条来源必须记录稳定证据编号、标题、机构、发布日期、访问日期、来源等级、URL、本地文件、覆盖主题和“提取事实”。只有链接或搜索摘要不算覆盖。媒体和机构材料仅保存元数据、有限摘录和研究摘要，禁止复制受保护全文。

## 必需数据表

- `group-quarterly.csv`：最近五季度集团收入、经营利润、净利润、经营现金流、资本开支、自由现金流和证据编号。
- `segments.csv`：最近五季度或可获得期间的分部收入、同比、调整 EBITA、利润率、关键经营指标和证据编号。
- `estimates.csv`：机构、日期、预测期、指标、原预测、新预测、依据、验证事件和证据编号。
- `peers.csv`：同行、报告期、指标、数值、可比性和证据编号。

无法获得填 `unavailable`；定义无法桥接填 `not_comparable`，不得填零或强行比较。

## 主张映射

`claims.json` 中每项重大判断包含主张编号、文本、证据类型、证据编号、反方解释和验证事件。报告中的重大事实和判断引用 `[E-NNN]`；编号必须能在 `index.md` 找到。

完成前运行：

```bash
python .agents/skills/financial-report-analysis/scripts/validate_research_package.py RESEARCH_DIR REPORT.md
```
