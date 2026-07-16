# Stock Research Skill Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a registered pure-technical research workflow supporting single-stock and multi-stock comparison, and migrate four core Skills to names that expose their evidence domain and output type.

**Architecture:** Persist index history into the existing `stock_daily` SQLite table, derive deterministic window metrics in a focused `src/technical_research.py` module, and persist a structured `technical_research` snapshot plus one Markdown report. Register the new workflow and artifact in `spec/`, then atomically rename the three existing research/decision Skills and add `stock-technical-research` without changing Chinese user intents.

**Tech Stack:** Python 3.12, pandas, numpy, SQLite/SQLAlchemy storage, pytest, YAML project registry, Markdown Skill contracts.

## Global Constraints

- `stock-technical-research` is pure technical research: never output buy/sell/add/reduce, position sizing, shares, or order instructions.
- Support both one code and multiple codes with one window and one benchmark policy.
- Default window is 90 natural days; always report actual trading-bar coverage.
- Quantitative statements must come from registered SQLite bars, indicator snapshots, or `artifact.report_context`; preserve missing data as `unavailable`.
- Keep company fundamentals, financial-statement quality, technical research, and position decisions as independent evidence domains.
- Only `stock-position-decision` may convert research into price, shares, triggers, targets, and invalidation.
- Use one consistent adjustment basis per comparison and disclose corporate-action gaps.
- Do not retain duplicate old/new Skill directories after migration; preserve old Chinese intent phrases in routes and descriptions.
- Preserve unrelated dirty-worktree changes and stage only files belonging to each task.

## File Structure

**Create:**

- `src/technical_research.py` — deterministic metrics, relative-strength calculations, stage classification, and structured payload assembly.
- `scripts/run_technical_research.py` — CLI orchestration, SQLite persistence, and Markdown rendering.
- `tests/test_technical_research.py` — unit tests for metrics, missing data, stages, and forbidden decision fields.
- `tests/test_technical_research_cli.py` — repository/CLI integration tests for single and comparison modes.
- `spec/workflows/technical-research.yaml` — registered workflow.
- `.agents/skills/stock-technical-research/SKILL.md` — pure technical research instructions.
- `.agents/skills/stock-technical-research/agents/openai.yaml` — generated UI metadata.

**Rename:**

- `.agents/skills/deep-stock-analysis/` → `.agents/skills/company-fundamental-research/`
- `.agents/skills/financial-report-analysis/` → `.agents/skills/financial-statement-quality/`
- `.agents/skills/decision-agent/` → `.agents/skills/stock-position-decision/`

**Modify:**

- `src/fetch_market.py` — persist the four registered index histories to `stock_daily`.
- `src/data_access.py` — allow `technical_research` snapshot queries.
- `spec/artifacts.yaml` — register `snapshot.index_bars` and `artifact.technical_research`.
- `spec/skills.yaml` — register renamed and new Skills.
- `spec/routes.yaml` — add technical research intents and point existing routes to renamed Skills.
- `spec/workflows/quant-analysis.yaml` — produce current index-bar input if required by registry consistency.
- `spec/workflows/deep-research.yaml`, `financial-report.yaml`, `position-decision.yaml`, `daily-report.yaml`, `weekly-report.yaml` — update Skill IDs and technical-research consumers.
- `scripts/check_project_spec.py` — register the twelfth workflow.
- `tests/spec/test_project_registry.py`, `test_workflow_contracts.py`, `test_skill_contracts.py`, `test_legacy_references.py` — enforce the new matrix and migration.
- `tests/test_deep_stock_analysis_skill.py`, `tests/test_financial_report_analysis_skill.py` — update paths and names while retaining behavior assertions.
- `AGENTS.md`, `references/skills-index.md`, `references/generated/workflows.md` — regenerate from `spec/`.
- Cross-references in `.agents/skills/daily-report/SKILL.md`, `.agents/skills/weekly-report/SKILL.md`, and renamed Skill files.

---

### Task 1: Establish RED Contract Tests for the Matrix

**Files:**

- Modify: `tests/spec/test_workflow_contracts.py`
- Modify: `tests/spec/test_project_registry.py`
- Modify: `tests/spec/test_skill_contracts.py`
- Create: `tests/test_technical_research.py`

**Interfaces:**

- Consumes: current `load_registry(ROOT / "spec")` and `.agents/skills/*/SKILL.md` contracts.
- Produces: failing expectations for `technical-research`, `artifact.technical_research`, the four normalized Skill IDs, and the no-trading boundary.

- [ ] **Step 1: Add failing registry and routing tests**

Add these assertions to `tests/spec/test_workflow_contracts.py`:

```python
def test_research_skill_matrix_is_explicit_and_technical_research_is_non_trading():
    registry = load_registry(ROOT / "spec")
    assert {
        "company-fundamental-research",
        "financial-statement-quality",
        "stock-technical-research",
        "stock-position-decision",
    } <= set(registry.skills)
    workflow = registry.workflows["technical-research"]
    assert workflow.skills == ("stock-technical-research",)
    assert "artifact.technical_research" in workflow.outputs
    assert not {"artifact.tracklist", "artifact.position"}.intersection(workflow.outputs)
    assert resolve_intent("技术分析 601138", registry).workflow == "technical-research"
    assert resolve_intent("技术对比 山东黄金 三花 工业富联", registry).workflow == "technical-research"
```

Add to `tests/spec/test_project_registry.py`:

```python
def test_technical_research_artifacts_are_registered():
    registry = load_registry(ROOT / "spec")
    index_bars = registry.artifacts["snapshot.index_bars"]
    assert index_bars.path == "data/stock_analysis.db"
    assert index_bars.storage == "sqlite_data_access"
    assert index_bars.kind == "bars"
    technical = registry.artifacts["artifact.technical_research"]
    assert technical.path == "data/stock_analysis.db"
    assert technical.storage == "sqlite_data_access"
    assert technical.kind == "technical_research"
    assert {"position-decision", "daily-report", "weekly-report"} <= set(technical.consumers)
```

- [ ] **Step 2: Add failing behavior-shape tests**

Create `tests/test_technical_research.py` with initial imports that do not yet exist:

```python
from src.technical_research import classify_stage, compare_payloads


def test_rsi_oversold_alone_is_not_a_bottom():
    result = classify_stage({
        "price_below_ma20": True,
        "ma_alignment": "bearish",
        "rsi6": 24.0,
        "adx14": 31.0,
        "plus_di14": 13.0,
        "minus_di14": 28.0,
        "cmf20": -0.12,
        "breakout_confirmed": False,
        "higher_low": False,
    })
    assert result["stage"] == "oversold_unstabilized"


def test_comparison_payload_has_no_trading_fields():
    result = compare_payloads([
        {"identity": {"code": "A"}, "stage": {"stage": "base_candidate", "confidence": 0.6}},
        {"identity": {"code": "B"}, "stage": {"stage": "downtrend_accelerating", "confidence": 0.8}},
    ])
    forbidden = {"action", "buy", "sell", "shares", "position_size", "entry_order"}
    assert forbidden.isdisjoint(result)
    assert [item["code"] for item in result["ranking"]] == ["A", "B"]
```

- [ ] **Step 3: Run RED tests and record expected failures**

Run:

```bash
source .venv/bin/activate
pytest tests/spec/test_workflow_contracts.py tests/spec/test_project_registry.py tests/test_technical_research.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'src.technical_research'`, and registry tests fail because `technical-research` and the new IDs do not exist.

- [ ] **Step 4: Commit the RED tests**

```bash
git add tests/spec/test_workflow_contracts.py tests/spec/test_project_registry.py tests/test_technical_research.py
git commit -m "test: define stock research skill matrix contracts"
```

---

### Task 2: Implement Deterministic Technical-Research Analytics

**Files:**

- Create: `src/technical_research.py`
- Modify: `tests/test_technical_research.py`

**Interfaces:**

- Consumes: `pandas.DataFrame` indexed by date with `open`, `high`, `low`, `close`, `volume`, `amount`; current indicator mappings from `snapshot.indicators`.
- Produces: `analyze_security(code, name, bars, indicators, benchmarks, window_days) -> dict`, `classify_stage(features) -> dict`, and `compare_payloads(payloads) -> dict`.

- [ ] **Step 1: Add failing tests for price, volume, amplitude, and relative strength**

Append fixtures and assertions:

```python
import pandas as pd
from src.technical_research import analyze_security


def _bars(closes, volumes):
    index = pd.date_range("2026-04-01", periods=len(closes), freq="B")
    close = pd.Series(closes, index=index, dtype=float)
    return pd.DataFrame({
        "open": close.shift(1).fillna(close.iloc[0]),
        "high": close * 1.02,
        "low": close * 0.98,
        "close": close,
        "volume": volumes,
        "amount": close * volumes,
    })


def test_analyze_security_uses_one_window_and_reports_actual_coverage():
    stock = _bars([10, 12, 11, 9, 9.5], [100, 120, 140, 160, 110])
    bench = _bars([10, 10.2, 10.1, 10.0, 9.9], [100] * 5)
    result = analyze_security("A", "Alpha", stock, {}, {"000001": bench}, 90)
    assert result["window"]["requested_natural_days"] == 90
    assert result["window"]["actual_bars"] == 5
    assert result["price_path"]["period_return"] == pytest.approx(-0.05)
    assert result["price_path"]["high"] == pytest.approx(12.24)
    assert result["volume"]["up_down_volume_ratio"] is not None
    assert result["relative_strength"]["000001"]["excess_return"] == pytest.approx(-0.04)


def test_missing_benchmark_is_unavailable_not_zero():
    result = analyze_security("A", "Alpha", _bars([10, 9], [100, 80]), {}, {}, 90)
    assert result["relative_strength"] == {"status": "unavailable", "reason": "benchmark_missing"}
```

- [ ] **Step 2: Run focused tests to verify the new failures**

Run `source .venv/bin/activate && pytest tests/test_technical_research.py -q`.

Expected: FAIL because `analyze_security` is absent.

- [ ] **Step 3: Implement the minimal analytics module**

Create `src/technical_research.py` with these public functions and payload shape:

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.quant.models import json_safe, normalize_bars

STAGE_ORDER = {
    "right_side_confirmed": 5,
    "trend_continuation": 4,
    "base_candidate": 3,
    "oversold_unstabilized": 2,
    "downtrend_accelerating": 1,
    "unavailable": 0,
}


def classify_stage(features: Mapping[str, Any]) -> dict[str, Any]:
    if features.get("breakout_confirmed") and features.get("plus_di14", 0) > features.get("minus_di14", 0):
        return {"stage": "right_side_confirmed", "confidence": 0.8}
    if features.get("higher_low") and not features.get("price_below_ma20") and features.get("cmf20", 0) >= 0:
        return {"stage": "base_candidate", "confidence": 0.7}
    if features.get("rsi6") is not None and features["rsi6"] < 30:
        return {"stage": "oversold_unstabilized", "confidence": 0.7}
    if features.get("ma_alignment") == "bearish" and features.get("adx14", 0) >= 25:
        return {"stage": "downtrend_accelerating", "confidence": 0.8}
    return {"stage": "unavailable", "confidence": 0.0}


def _window_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    returns = frame["close"].pct_change()
    amplitude = (frame["high"] - frame["low"]) / frame["close"].shift(1)
    drawdown = frame["close"] / frame["close"].cummax() - 1
    last20, previous20 = frame.tail(20), frame.iloc[-40:-20]
    up_volume = frame.loc[returns > 0, "volume"].mean()
    down_volume = frame.loc[returns < 0, "volume"].mean()
    return json_safe({
        "period_return": frame["close"].iloc[-1] / frame["close"].iloc[0] - 1,
        "high": frame["high"].max(),
        "high_date": frame["high"].idxmax(),
        "low": frame["low"].min(),
        "low_date": frame["low"].idxmin(),
        "max_drawdown": drawdown.min(),
        "realized_volatility": returns.std() * np.sqrt(252),
        "average_amplitude": amplitude.mean(),
        "last20_amplitude": ((last20["high"] - last20["low"]) / last20["close"].shift(1)).mean(),
        "previous20_amplitude": None if previous20.empty else ((previous20["high"] - previous20["low"]) / previous20["close"].shift(1)).mean(),
        "last20_vs_previous20_volume": None if previous20.empty else last20["volume"].mean() / previous20["volume"].mean(),
        "up_down_volume_ratio": up_volume / down_volume if down_volume else None,
    })
```

Implement `analyze_security` by slicing the requested natural-day window, calling `_window_metrics`, merging only registered indicator keys, calculating benchmark correlation/beta/excess return on common dates, building support/resistance/confirmation/falsification fields, and passing observable features to `classify_stage`. Implement `compare_payloads` by sorting descending on `STAGE_ORDER` and returning only `ranking`, `common_window`, `benchmarks`, and `evidence_gaps`.

- [ ] **Step 4: Run tests and refine only the required stage rules**

Run `source .venv/bin/activate && pytest tests/test_technical_research.py -q`.

Expected: all tests in the file PASS; no runtime warnings or non-finite JSON values.

- [ ] **Step 5: Commit deterministic analytics**

```bash
git add src/technical_research.py tests/test_technical_research.py
git commit -m "feat: add deterministic technical structure analytics"
```

---

### Task 3: Register and Persist Three-Month Index History

**Files:**

- Modify: `src/fetch_market.py`
- Modify: `tests/test_fetch_storage.py`
- Modify: `spec/artifacts.yaml`

**Interfaces:**

- Consumes: AkShare index frames for `000001`, `399001`, `399006`, `000688`.
- Produces: normalized `stock_daily` rows with those codes and a `snapshot.index_bars` registry entry.

- [ ] **Step 1: Add a failing index-persistence test**

In `tests/test_fetch_storage.py`, inject a two-row AkShare frame and assert:

```python
def test_fetch_market_persists_registered_index_history(tmp_storage, monkeypatch):
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2026-07-15", "2026-07-16"]),
        "open": [3900.0, 3912.0], "high": [3950.0, 3940.0],
        "low": [3890.0, 3867.0], "close": [3955.0, 3882.0],
        "volume": [1_000.0, 1_200.0],
    })
    monkeypatch.setattr("src.fetch_market.ak.stock_zh_index_daily", lambda symbol: frame.copy())
    result = fetch_and_save_index_history(tmp_storage, lookback_days=90)
    assert result == {"000001": 2, "399001": 2, "399006": 2, "000688": 2}
    assert len(tmp_storage.get_stock_daily("000001", limit=10)) == 2
```

- [ ] **Step 2: Run the focused test and verify RED**

Run `source .venv/bin/activate && pytest tests/test_fetch_storage.py::test_fetch_market_persists_registered_index_history -q`.

Expected: FAIL because `fetch_and_save_index_history` does not exist.

- [ ] **Step 3: Implement normalized persistence**

Add `fetch_and_save_index_history(storage, lookback_days: int = 120) -> dict[str, int]` to `src/fetch_market.py`. Reuse the existing index symbol map, normalize column names to the `stock_daily` contract, filter by `today - timedelta(days=lookback_days)`, and call the existing storage daily-bar upsert for each index code. Keep the existing `data/market/index.json` current-summary behavior unchanged.

- [ ] **Step 4: Register the index-bar artifact**

Add to `spec/artifacts.yaml`:

```yaml
- id: snapshot.index_bars
  path: data/stock_analysis.db
  storage: sqlite_data_access
  kind: bars
  producer: data-preparation
  consumers: [quant-analysis, technical-research]
  freshness: trading_day
  missing: block
```

Also add `snapshot.index_bars` to the outputs of `data-preparation` and the inputs/preflight of `technical-research` in Task 5.

- [ ] **Step 5: Verify storage tests**

Run `source .venv/bin/activate && pytest tests/test_fetch_storage.py tests/test_data_access.py -q`.

Expected: PASS.

- [ ] **Step 6: Commit index history persistence**

```bash
git add src/fetch_market.py tests/test_fetch_storage.py spec/artifacts.yaml
git commit -m "feat: persist registered index history"
```

---

### Task 4: Add CLI, Structured Snapshot, and Markdown Rendering

**Files:**

- Create: `scripts/run_technical_research.py`
- Create: `tests/test_technical_research_cli.py`
- Modify: `src/data_access.py`
- Modify: `src/storage.py` only if an existing generic `save_snapshot`/`load_snapshot` interface cannot express the new kind.

**Interfaces:**

- Consumes: `--codes`, `--window-days`, `--as-of`, registered bars/indicators/index bars.
- Produces: `stock_snapshots(kind="technical_research")` per code, optional comparison snapshot under a deterministic composite code, and exactly one Markdown report.

- [ ] **Step 1: Add failing single/comparison CLI tests**

Create tests that invoke `main([...], root=tmp_path, storage=fake_storage)` and assert:

```python
def test_single_mode_writes_one_report_and_snapshot(repo_fixture):
    result = run(["--codes", "601138", "--as-of", "2026-07-16"], repo_fixture)
    assert result["mode"] == "single"
    assert result["report"] == "tracking/601138-工业富联/technical/2026-07-16.md"
    assert repo_fixture.snapshot("601138", "technical_research")["stage"]


def test_comparison_mode_uses_one_window_and_one_markdown(repo_fixture):
    result = run(["--codes", "600547,002050,601138", "--window-days", "90", "--as-of", "2026-07-16"], repo_fixture)
    assert result["mode"] == "comparison"
    assert result["report"] == "tracking/technical/2026-07-16-002050-600547-601138.md"
    assert len(list(repo_fixture.root.glob("tracking/technical/*.md"))) == 1
```

- [ ] **Step 2: Run tests and verify RED**

Run `source .venv/bin/activate && pytest tests/test_technical_research_cli.py -q`.

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement the runner**

Expose:

```python
def run(argv: list[str] | None = None, *, root: Path = ROOT, storage=None) -> dict:
    ...

def render_markdown(payload: dict) -> str:
    ...
```

The renderer must use this section order:

```text
# 技术结构研究
## 一、数据范围与证据质量
## 二、指数环境
## 三、价格路径
## 四、趋势与动量
## 五、量价资金
## 六、振幅与波动
## 七、技术阶段、确认与证伪
## 多股横向比较（comparison only）
```

Forbid action verbs in generated conclusions by constructing only stage/confirmation/falsification fields. Persist each structured payload through `storage.save_snapshot(code, "technical_research", payload, as_of=...)`. Add `technical_research` to the accepted `src.data_access.query_payload` kinds.

- [ ] **Step 4: Verify runner and data-access tests**

Run:

```bash
source .venv/bin/activate
pytest tests/test_technical_research_cli.py tests/test_data_access.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the runner**

```bash
git add scripts/run_technical_research.py src/data_access.py src/storage.py tests/test_technical_research_cli.py tests/test_data_access.py
git commit -m "feat: persist and render technical research"
```

---

### Task 5: Create and Register `stock-technical-research`

**Files:**

- Create: `.agents/skills/stock-technical-research/SKILL.md`
- Create: `.agents/skills/stock-technical-research/agents/openai.yaml`
- Create: `spec/workflows/technical-research.yaml`
- Modify: `spec/skills.yaml`
- Modify: `spec/routes.yaml`
- Modify: `spec/artifacts.yaml`
- Modify: `scripts/check_project_spec.py`
- Modify: `tests/spec/test_skill_contracts.py`

**Interfaces:**

- Consumes: `snapshot.bars`, `snapshot.quote`, `snapshot.indicators`, `snapshot.index_bars`, `artifact.report_context`.
- Produces: `artifact.technical_research`.

- [ ] **Step 1: Run the Skill baseline tests and retain failure output**

Run the Task 1 registry/contract tests before creating the Skill. Expected: failures for the absent workflow, route, artifact, and Skill directory. This is the RED baseline required by `writing-skills`.

- [ ] **Step 2: Initialize the new Skill using the required scaffold tool**

Run:

```bash
python /Users/majiang/.codex/skills/.system/skill-creator/scripts/init_skill.py stock-technical-research \
  --path .agents/skills \
  --interface display_name="股票技术面研究" \
  --interface short_description="分析指数环境、价格路径、量价、振幅与技术阶段" \
  --interface default_prompt="使用 $stock-technical-research 对指定股票做纯技术研究，不输出交易指令。"
```

- [ ] **Step 3: Replace the scaffold with the approved contract**

Write `SKILL.md` with exactly two frontmatter fields and this project contract:

```markdown
---
name: stock-technical-research
description: Use when users request stock technical analysis, technical comparison, price-volume structure, amplitude or volatility analysis, bottom-stage assessment, or multi-month chart and indicator interpretation; excludes company-quality research and trading decisions.
---

# 股票技术面研究

## Project contract

- Workflow: `technical-research`
- Policies: `DATA.QUALITY`
- Consumes: `snapshot.bars`, `snapshot.quote`, `snapshot.indicators`, `snapshot.index_bars`, `artifact.report_context`
- Produces: `artifact.technical_research`
```

Follow it with imperative instructions for preflight, single/comparison modes, the seven-layer framework, the five stages, evidence-gap handling, and the explicit pure-research boundary. Reference `$fetch-data`, `$tech-indicators`, and `$market-regime` as required upstream Skills; reference `$stock-position-decision` as the only downstream trading Skill.

- [ ] **Step 4: Register workflow, route, artifact, and Skill**

Add `spec/workflows/technical-research.yaml`:

```yaml
id: technical-research
inputs: [snapshot.bars, snapshot.quote, snapshot.indicators, snapshot.index_bars, artifact.report_context]
optional_inputs: []
outputs: [artifact.technical_research]
policies: [DATA.QUALITY]
skills: [stock-technical-research]
steps:
  - refresh registered stock and index bars and current indicator snapshots
  - compute one-window price volume amplitude volatility momentum and relative-strength evidence
  - classify each stock into one technical stage with confirmation and falsification conditions
  - render one single-stock or comparison Markdown report and persist the structured summary
  - exclude company-quality judgments and trading instructions
preflight: [snapshot.bars, snapshot.quote, snapshot.indicators, snapshot.index_bars, artifact.report_context]
completion: [DATA.REGISTERED_CURRENT, artifact.technical_research]
on_failure: [retry stale registered inputs, preserve unavailable gaps, stop before stage conclusions when required price history is missing]
```

Register `artifact.technical_research` as SQLite kind `technical_research`, producer `technical-research`, consumers `[position-decision, daily-report, weekly-report]`, freshness `trading_day`, missing `unavailable`. Add a priority-100 route with intents `技术分析 {code}`, `技术对比 {codes}`, `量价分析 {code}`, `技术结构 {code}`.

- [ ] **Step 5: Validate the new Skill folder and focused contracts**

Run:

```bash
python /Users/majiang/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/stock-technical-research
source .venv/bin/activate
pytest tests/spec/test_skill_contracts.py tests/spec/test_workflow_contracts.py tests/spec/test_project_registry.py -q
```

Expected: Skill validation PASS; remaining failures only reference the three old Skill names pending Task 6.

- [ ] **Step 6: Commit the new Skill and workflow**

```bash
git add .agents/skills/stock-technical-research spec/workflows/technical-research.yaml spec/skills.yaml spec/routes.yaml spec/artifacts.yaml scripts/check_project_spec.py tests/spec
git commit -m "feat: register pure technical stock research skill"
```

---

### Task 6: Atomically Rename the Existing Research and Decision Skills

**Files:**

- Rename the three directories listed in File Structure.
- Modify: their `SKILL.md` frontmatter and cross-references.
- Modify: `spec/skills.yaml`, `spec/routes.yaml`, and affected `spec/workflows/*.yaml`.
- Modify: affected tests and scheduled prompt strings.

**Interfaces:**

- Consumes: unchanged workflow IDs `deep-research`, `financial-report`, `position-decision`.
- Produces: normalized Skill IDs while preserving route intent and workflow behavior.

- [ ] **Step 1: Update failing tests to require only normalized IDs**

Change route expectations:

```python
("深度分析 002050", "deep-research", "deep-research", "company-fundamental-research")
("财报分析 9988", "financial-report", "financial-report", "financial-statement-quality")
("建仓分析 002050", "position-decision", "position-decision", "stock-position-decision")
```

Add assertions that old IDs are absent from `registry.skills` and old directories do not exist.

- [ ] **Step 2: Verify RED before renaming**

Run `source .venv/bin/activate && pytest tests/spec/test_workflow_contracts.py tests/spec/test_project_registry.py tests/spec/test_skill_contracts.py -q`.

Expected: FAIL because old IDs and directories still exist.

- [ ] **Step 3: Rename directories and frontmatter**

Use `mv` for each directory, then update only the frontmatter `name`, human heading, downstream Skill references, and project contract reverse links. Preserve the existing domain instructions and exclusions.

- [ ] **Step 4: Update registry and workflow reverse links**

Replace the Skill IDs in `spec/skills.yaml`, the route `skill` fields, and workflow `skills` arrays. Add `artifact.technical_research` to `position-decision`, `daily-report`, and `weekly-report` inputs; describe it as technical evidence rather than a trading decision.

- [ ] **Step 5: Update all live references and prove no stale IDs remain**

Run:

```bash
rg -n 'deep-stock-analysis|financial-report-analysis|decision-agent' \
  AGENTS.md spec .agents scripts tests references tracking/README.md src/README.md
```

Expected: no live contract hits. Historical reports under `tracking/` are excluded from forced migration.

- [ ] **Step 6: Run focused migration tests**

Run:

```bash
source .venv/bin/activate
pytest tests/spec/test_workflow_contracts.py tests/spec/test_project_registry.py \
  tests/spec/test_skill_contracts.py tests/test_deep_stock_analysis_skill.py \
  tests/test_financial_report_analysis_skill.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit the atomic rename**

```bash
git add .agents/skills spec scripts tests references
git commit -m "refactor: normalize stock research skill names"
```

---

### Task 7: Regenerate Documentation and Run Full Verification

**Files:**

- Modify generated regions: `AGENTS.md`, `references/skills-index.md`, `references/generated/workflows.md`.
- Modify: `data/spec/verification.json` only if the development workflow requires a fresh verification record.

**Interfaces:**

- Consumes: final registry and implementation.
- Produces: deterministic documentation, clean project specification, full test evidence, and final commits.

- [ ] **Step 1: Regenerate registered documentation**

Run:

```bash
source .venv/bin/activate
python - <<'PY'
from pathlib import Path
from src.spec.generator import generate_documents
from src.spec.loader import load_registry
root = Path.cwd()
generate_documents(load_registry(root / "spec"), root)
PY
```

- [ ] **Step 2: Run placeholder, forbidden-action, and stale-name scans**

Run:

```bash
rg -n 'TBD|TODO|placeholder' .agents/skills/stock-technical-research spec/workflows/technical-research.yaml
rg -n '买入|卖出|加仓|减仓|股数|仓位|position_size|shares' .agents/skills/stock-technical-research/SKILL.md
rg -n 'deep-stock-analysis|financial-report-analysis|decision-agent' AGENTS.md spec .agents scripts tests references
```

Expected: first and third commands produce no hits; second command may contain only the explicit prohibition sentence and tests asserting forbidden output.

- [ ] **Step 3: Run the complete targeted verification**

Run:

```bash
source .venv/bin/activate
pytest tests/test_technical_research.py tests/test_technical_research_cli.py tests/spec -q
python scripts/check_project_spec.py
python /Users/majiang/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/stock-technical-research
```

Expected: all tests PASS, `specification valid`, `generated documentation current`, and Skill validation PASS.

- [ ] **Step 4: Run the full repository suite**

Run `source .venv/bin/activate && pytest -q`.

Expected: zero failures. Preserve unrelated pre-existing failures as explicit blockers rather than changing unrelated code.

- [ ] **Step 5: Smoke-test both modes on current registered data**

Run:

```bash
source .venv/bin/activate
python scripts/run_technical_research.py --codes 601138 --window-days 90 --as-of 2026-07-16
python scripts/run_technical_research.py --codes 600547,002050,601138 --window-days 90 --as-of 2026-07-16
```

Expected: one single-stock Markdown, one multi-stock Markdown, structured snapshots with non-empty stages, and no trading action fields.

- [ ] **Step 6: Inspect final diff and commit generated docs/verification**

```bash
git diff --check
git status --short
git add AGENTS.md references/skills-index.md references/generated/workflows.md data/spec/verification.json
git commit -m "docs: publish stock research skill matrix"
```

- [ ] **Step 7: Request code review before completion**

Use `requesting-code-review` against the design, this plan, the final diff, and fresh verification outputs. Address any blocking findings with a new failing test before implementation changes.

