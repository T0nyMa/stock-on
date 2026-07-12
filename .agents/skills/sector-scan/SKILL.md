---
name: sector-scan
description: 板块强度扫描 — 20个AI/科技细分赛道排名，发现最强/最弱板块
---

# 板块强度扫描

## Project contract

- workflow: discovery
- consumes: `snapshot.indicators`, `artifact.strategy_scan`
- produces: `artifact.discovery_report`
- policies: `DATA.QUALITY`, `RESEARCH.EVIDENCE`

对 20 个 AI/科技细分赛道的 78 只代表股做批量行情分析，计算板块强度排名。

## 用法

`$sector-scan` 或用户说"板块扫描""板块排名""热点板块"

## 输入

`tracking/sectors.json` — 20 个板块定义，每板块 4 只代表股

## 流程

```bash
source .venv/bin/activate && python src/sector_scan.py
```

输出：
- `data/market/sector_scan.json` — JSON 数据
- `tracking/sectors/YYYY-MM-DD-sector-scan.md` — Markdown 报告

## 评分方法

```
板块强度 = 均涨幅×0.4 + 上涨占比×0.3 + 均成交额×0.2 + 最强股涨幅×0.1
```

## 输出

- 20 板块排名表
- 每板块明细（4只代表股涨跌/成交）
- 最强/最弱板块标注

## 完成标志

- [ ] sector_scan.py 已执行
- [ ] JSON + MD 报告已写入
