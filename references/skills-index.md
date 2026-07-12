# Skills 索引

Skill 的用途边界由 `spec/skills.yaml` 登记，具体执行方式以各 `SKILL.md` 为准。下表为生成内容，不要手工编辑标记区域。

<!-- BEGIN GENERATED: skills -->
| Skill ID | 分类 | 路径 | Workflows | 排除范围 |
|---|---|---|---|---|
| `daily-report` | `reporting` | `.agents/skills/daily-report/SKILL.md` | `daily-report` | — |
| `decision-agent` | `decision` | `.agents/skills/decision-agent/SKILL.md` | `position-decision` | — |
| `deep-stock-analysis` | `research` | `.agents/skills/deep-stock-analysis/SKILL.md` | `deep-research` | `trading_advice` |
| `deploy` | `publishing` | `.agents/skills/deploy/SKILL.md` | `deploy`<br>`daily-report`<br>`weekly-report` | — |
| `discovery` | `discovery` | `.agents/skills/discovery/SKILL.md` | `discovery` | — |
| `fetch-data` | `data` | `.agents/skills/fetch-data/SKILL.md` | `data-preparation` | — |
| `financial-report-analysis` | `research` | `.agents/skills/financial-report-analysis/SKILL.md` | `financial-report` | `valuation`<br>`trading_advice` |
| `market-regime` | `analysis` | `.agents/skills/market-regime/SKILL.md` | `quant-analysis` | — |
| `screener` | `discovery` | `.agents/skills/screener/SKILL.md` | `discovery` | — |
| `sector-scan` | `discovery` | `.agents/skills/sector-scan/SKILL.md` | `discovery` | — |
| `strategy-bottom-volume` | `strategy` | `.agents/skills/strategy-bottom-volume/SKILL.md` | — | — |
| `strategy-box-oscillation` | `strategy` | `.agents/skills/strategy-box-oscillation/SKILL.md` | — | — |
| `strategy-bull-trend` | `strategy` | `.agents/skills/strategy-bull-trend/SKILL.md` | — | — |
| `strategy-chan-theory` | `strategy` | `.agents/skills/strategy-chan-theory/SKILL.md` | — | — |
| `strategy-dragon-head` | `strategy` | `.agents/skills/strategy-dragon-head/SKILL.md` | — | — |
| `strategy-emotion-cycle` | `strategy` | `.agents/skills/strategy-emotion-cycle/SKILL.md` | — | — |
| `strategy-event-driven` | `strategy` | `.agents/skills/strategy-event-driven/SKILL.md` | — | — |
| `strategy-executor` | `strategy` | `.agents/skills/strategy-executor/SKILL.md` | `strategy-analysis` | — |
| `strategy-expectation-repricing` | `strategy` | `.agents/skills/strategy-expectation-repricing/SKILL.md` | — | — |
| `strategy-growth-quality` | `strategy` | `.agents/skills/strategy-growth-quality/SKILL.md` | — | — |
| `strategy-hot-theme` | `strategy` | `.agents/skills/strategy-hot-theme/SKILL.md` | — | — |
| `strategy-ma-golden-cross` | `strategy` | `.agents/skills/strategy-ma-golden-cross/SKILL.md` | — | — |
| `strategy-one-yang-three-yin` | `strategy` | `.agents/skills/strategy-one-yang-three-yin/SKILL.md` | — | — |
| `strategy-shrink-pullback` | `strategy` | `.agents/skills/strategy-shrink-pullback/SKILL.md` | — | — |
| `strategy-volume-breakout` | `strategy` | `.agents/skills/strategy-volume-breakout/SKILL.md` | — | — |
| `strategy-wave-theory` | `strategy` | `.agents/skills/strategy-wave-theory/SKILL.md` | — | — |
| `tech-indicators` | `data` | `.agents/skills/tech-indicators/SKILL.md` | `quant-analysis` | — |
| `weekly-report` | `reporting` | `.agents/skills/weekly-report/SKILL.md` | `weekly-report` | — |
<!-- END GENERATED: skills -->

## 使用方式

先从 `AGENTS.md` 的意图路由确定 workflow，再读取 workflow 登记的 Skill。策略 Skill 由策略分析工作流按市场状态选择，不应仅凭名称直接组合。
