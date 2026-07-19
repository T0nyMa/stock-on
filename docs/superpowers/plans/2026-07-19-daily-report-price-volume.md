# Daily Report Price-Volume Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic price-volume metrics and interpretation to every held-stock and core-stock card in the registered daily report workflow.

**Architecture:** Extend the existing focused `src/daily_metrics.py` module into the sole calculator for daily price-volume evidence. `src.quant.pipeline` will attach its nullable result to each stock in `data/report_context.json`; the daily-report template and Skill will require rendering that registered object without recalculation.

**Tech Stack:** Python 3, pandas-backed normalized OHLCV records, pytest, JSON report context, Markdown Skill/template files.

## Global Constraints

- Cover all `has_position=true` stocks and the fixed daily core set; deduplicate by market and code.
- A/H markets remain separate; never use A-share metrics as H-share evidence.
- `volume_vs_ma20` is the primary volume-state signal; 5-day and intraday volume ratios are supplementary.
- Missing history, zero denominators and absent source fields render as `unavailable`; never guess.
- Price-volume research does not directly generate trading instructions.
- Preserve the daily report's seven-section structure.
- The current worktree contains pre-existing uncommitted changes in `src/daily_metrics.py`, `tests/test_daily_metrics.py`, `src/report_lib.py`, and `scripts/fetch_all_daily.py`; inspect and preserve them instead of replacing them wholesale.

---

## File Map

- `src/daily_metrics.py`: sole deterministic price-volume derivation and classification.
- `tests/test_daily_metrics.py`: unit tests for formulas, classification, missing data and market isolation inputs.
- `src/quant/pipeline.py`: attaches `price_volume` to each registered stock snapshot/report-context entry.
- `tests/test_quant_pipeline.py`: verifies context persistence and unavailable behavior.
- `src/report_lib.py`: backward-compatible consumer of the expanded daily metrics for legacy daily snapshot paths.
- `scripts/fetch_all_daily.py`: serializes the expanded metrics into `data/daily_snapshot.json` without new formulas.
- `references/templates/daily-report-v2.md`: adds one price-volume line to held and core stock cards.
- `.agents/skills/daily-report/SKILL.md`: requires the price-volume evidence for held/core coverage.
- `tests/spec/test_skill_contracts.py`: checks the Skill and template contract.

### Task 1: Expand the Deterministic Price-Volume Calculator

**Files:**
- Modify: `src/daily_metrics.py`
- Modify: `tests/test_daily_metrics.py`

**Interfaces:**
- Consumes: `derive_daily_metrics(bars, *, indicators=None, quote=None, window_days=90)`, where `bars` is chronological OHLCV mappings.
- Produces: a JSON-safe mapping containing existing fields plus `price_change_pct`, `intraday_volume_ratio`, `volume_vs_ma5`, `volume_vs_ma20`, `recent20_vs_previous20`, `up_down_volume_ratio_90d`, `mfi14`, `cmf20`, `obv_20d_direction`, `turnover_rate`, `volume_state`, `price_volume_label`, `interpretation_flags`, and `evidence_gaps`.

- [ ] **Step 1: Add failing tests for the complete metric contract**

Append test helpers and assertions equivalent to:

```python
from datetime import date, timedelta


def make_bars(count, *, latest_volume=240, rising=True):
    start = date(2026, 1, 1)
    bars = []
    for index in range(count):
        close = 10 + index * 0.1 if rising else 20 - index * 0.1
        bars.append({
            "date": (start + timedelta(days=index)).isoformat(),
            "open": close - 0.05,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": 100,
            "amount": close * 100,
        })
    bars[-1]["volume"] = latest_volume
    return bars


def test_classifies_expanding_up_day_and_fund_flow_confirmation():
    result = derive_daily_metrics(
        make_bars(61, latest_volume=500),
        indicators={"mfi14": 62.5, "cmf20": 0.08, "obv_series": list(range(61))},
        quote={"volume_ratio": 1.8, "turnover_rate": 2.4},
    )
    assert result["volume_state"] == "expanding"
    assert result["price_volume_label"] == "放量上涨"
    assert result["volume_vs_ma20"] >= 1.20
    assert result["mfi14"] == 62.5
    assert result["cmf20"] == 0.08
    assert result["obv_20d_direction"] == "rising"


def test_labels_local_expansion_inside_medium_term_contraction():
    bars = make_bars(40, latest_volume=150)
    for item in bars[:20]:
        item["volume"] = 300
    result = derive_daily_metrics(bars)
    assert result["volume_vs_ma5"] >= 1.20
    assert result["recent20_vs_previous20"] <= 0.80
    assert "local_expansion_medium_contraction" in result["interpretation_flags"]


def test_returns_unavailable_instead_of_guessing():
    result = derive_daily_metrics([{"date": "2026-07-17", "close": 10, "volume": 0}])
    assert result["volume_vs_ma20"] is None
    assert result["recent20_vs_previous20"] is None
    assert result["obv_20d_direction"] == "unavailable"
    assert result["volume_state"] == "unavailable"
    assert "history_lt_20" in result["evidence_gaps"]
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```bash
.venv/bin/pytest tests/test_daily_metrics.py -q
```

Expected: failures for the new keyword arguments and missing output fields, while the two existing baseline tests continue to describe legacy behavior.

- [ ] **Step 3: Implement nullable helpers and classification**

Implement in `src/daily_metrics.py`:

```python
def derive_daily_metrics(bars, *, indicators=None, quote=None, window_days=90):
    indicators = indicators or {}
    quote = quote or {}
    # Preserve existing keys, filter the natural-day window from the latest
    # dated row, then calculate ratios only when minimum history exists.
```

Use these exact thresholds:

```python
if volume_vs_ma20 is None:
    volume_state = "unavailable"
elif volume_vs_ma20 >= 1.20:
    volume_state = "expanding"
elif volume_vs_ma20 <= 0.80:
    volume_state = "contracting"
else:
    volume_state = "normal"
```

Determine `price_volume_label` from the latest close return and `volume_state`. Add `local_expansion_medium_contraction` only when `volume_vs_ma5 >= 1.20` and `recent20_vs_previous20 <= 0.80`. Treat booleans, non-finite numbers and zero denominators as unavailable.

For `obv_20d_direction`, consume an explicitly supplied `obv_series`; return `rising`, `falling`, `flat`, or `unavailable`. Do not reconstruct an OBV series from a single snapshot scalar.

- [ ] **Step 4: Add boundary tests**

Add parameterized tests for histories of 1, 5, 20, 39 and 40 bars, zero-volume windows, no up days, no down days, negative-price day with expanding volume, and flat OBV:

```python
def test_expanding_down_day_with_negative_cmf_is_negative_structure():
    bars = make_bars(61, latest_volume=500, rising=False)
    result = derive_daily_metrics(
        bars,
        indicators={"cmf20": -0.12, "mfi14": 25, "obv_series": list(range(61, 0, -1))},
    )
    assert result["price_volume_label"] == "放量下跌"
    assert "negative_flow_confirmation" in result["interpretation_flags"]
```

- [ ] **Step 5: Run unit tests and commit**

Run:

```bash
.venv/bin/pytest tests/test_daily_metrics.py -q
git diff --check
```

Expected: all daily-metric tests pass and no whitespace errors.

Commit only the calculator and its tests:

```bash
git add src/daily_metrics.py tests/test_daily_metrics.py
git commit -m "feat: derive daily price-volume structure"
```

### Task 2: Persist Price-Volume Evidence in Report Context

**Files:**
- Modify: `src/quant/pipeline.py`
- Modify: `tests/test_quant_pipeline.py`

**Interfaces:**
- Consumes: Task 1 `derive_daily_metrics(...)`.
- Produces: `snapshot["price_volume"]` for each stock, persisted under `data/report_context.json -> stocks -> {code} -> price_volume`.

- [ ] **Step 1: Add failing pipeline tests**

Create fixtures with 61 chronological bars and assert:

```python
def test_stock_snapshot_contains_registered_price_volume():
    snapshot = build_stock_snapshot(
        "601899", "紫金矿业", records_61,
        source_evidence={"source": "test", "gaps": []},
        as_of="2026-07-17",
    )
    assert snapshot["price_volume"]["volume_vs_ma20"] is not None
    assert snapshot["price_volume"]["price_volume_label"] in {
        "放量上涨", "缩量上涨", "放量下跌", "缩量下跌", "正常量能",
    }


def test_stock_snapshot_preserves_unavailable_price_volume():
    snapshot = build_stock_snapshot("02050", "三花智控H", [], as_of="2026-07-17")
    assert snapshot["price_volume"]["volume_state"] == "unavailable"
    assert "history_lt_20" in snapshot["price_volume"]["evidence_gaps"]
```

- [ ] **Step 2: Run the pipeline tests and confirm RED**

Run:

```bash
.venv/bin/pytest tests/test_quant_pipeline.py -q
```

Expected: failures because `price_volume` does not yet exist.

- [ ] **Step 3: Attach the deterministic object**

Import `derive_daily_metrics` in `src/quant/pipeline.py`. In `build_stock_snapshot`, after `compute_indicators(frame)`, construct:

```python
price_volume = derive_daily_metrics(
    records,
    indicators={
        "mfi14": indicators.get("mfi14"),
        "cmf20": indicators.get("cmf20"),
    },
)
```

The current quant module exposes only the current OBV scalar, so pass no `obv_series` and retain `obv_20d_direction="unavailable"`; do not introduce a second OBV formula in this task. Add `"price_volume": price_volume` to the returned snapshot for both populated and empty histories.

- [ ] **Step 4: Verify repository persistence**

Run:

```bash
.venv/bin/pytest tests/test_quant_pipeline.py -q
.venv/bin/python scripts/run_quant_analysis.py --date 2026-07-17
jq '.stocks[\"601899\"].price_volume, .stocks[\"002050\"].price_volume' data/report_context.json
```

Expected: tests pass; both objects contain the full nullable schema. H-share objects with missing history remain unavailable.

- [ ] **Step 5: Commit**

```bash
git add src/quant/pipeline.py tests/test_quant_pipeline.py
git commit -m "feat: register price-volume report context"
```

### Task 3: Keep Legacy Daily Snapshot Consumers Compatible

**Files:**
- Modify: `src/report_lib.py`
- Modify: `scripts/fetch_all_daily.py`
- Modify: `tests/test_report_lib.py`

**Interfaces:**
- Consumes: expanded `derive_daily_metrics`.
- Produces: legacy stock dictionaries and `data/daily_snapshot.json` with the new fields, without any duplicated calculations.

- [ ] **Step 1: Add a failing compatibility test**

In `tests/test_report_lib.py`, mock registered bars, quote and indicators and assert that `load_all_stocks()` exposes:

```python
assert stock["volume_vs_ma20"] == expected
assert stock["price_volume_label"] == expected_label
assert stock["mfi14"] == indicator_snapshot["mfi14"]
assert stock["cmf20"] == indicator_snapshot["cmf20"]
```

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
.venv/bin/pytest tests/test_report_lib.py -q
```

Expected: missing new keys or missing keyword inputs.

- [ ] **Step 3: Pass registered inputs into the calculator**

Change `src/report_lib.py` to call:

```python
daily_metrics = derive_daily_metrics(
    bars,
    indicators={
        "mfi14": quantitative_snapshot.get("mfi14"),
        "cmf20": quantitative_snapshot.get("cmf20"),
    },
    quote=q,
)
```

Use the already loaded quantitative snapshot when available. Preserve existing legacy keys such as `volume_ratio_5d`, `volume_change_vs_prev`, `amount_change_vs_prev`, `amplitude`, and `close_position`.

- [ ] **Step 4: Serialize fields without formulas**

In `scripts/fetch_all_daily.py`, extend each `a_stocks` entry by copying:

```python
"volume_vs_ma5": s.get("volume_vs_ma5"),
"volume_vs_ma20": s.get("volume_vs_ma20"),
"recent20_vs_previous20": s.get("recent20_vs_previous20"),
"up_down_volume_ratio_90d": s.get("up_down_volume_ratio_90d"),
"mfi14": s.get("mfi14"),
"cmf20": s.get("cmf20"),
"obv_20d_direction": s.get("obv_20d_direction"),
"volume_state": s.get("volume_state"),
"price_volume_label": s.get("price_volume_label"),
"price_volume_gaps": s.get("evidence_gaps", []),
```

- [ ] **Step 5: Test and commit**

Run:

```bash
.venv/bin/pytest tests/test_daily_metrics.py tests/test_report_lib.py -q
git diff --check
```

Expected: all focused tests pass.

```bash
git add src/report_lib.py scripts/fetch_all_daily.py tests/test_report_lib.py
git commit -m "feat: expose price-volume daily snapshot fields"
```

### Task 4: Make Price-Volume Evidence Mandatory in Daily Report Cards

**Files:**
- Modify: `references/templates/daily-report-v2.md`
- Modify: `.agents/skills/daily-report/SKILL.md`
- Modify: `tests/spec/test_skill_contracts.py`

**Interfaces:**
- Consumes: `artifact.report_context.stocks.{code}.price_volume`.
- Produces: a stable “价量结构” line in held-stock and core-stock cards.

- [ ] **Step 1: Add failing contract tests**

Add:

```python
def test_daily_report_requires_price_volume_cards():
    skill = Path(".agents/skills/daily-report/SKILL.md").read_text(encoding="utf-8")
    template = Path("references/templates/daily-report-v2.md").read_text(encoding="utf-8")
    for token in (
        "volume_vs_ma5", "volume_vs_ma20", "recent20_vs_previous20",
        "up_down_volume_ratio_90d", "MFI", "CMF", "OBV",
    ):
        assert token in skill
    assert template.count("**价量结构**") >= 2
```

- [ ] **Step 2: Run and confirm RED**

Run:

```bash
.venv/bin/pytest tests/spec/test_skill_contracts.py -q
```

Expected: failure because the Skill and template do not contain the complete contract.

- [ ] **Step 3: Update the template**

Add to the second-section position card and third-section core card:

```markdown
- **价量结构**：量比 {{intraday_volume_ratio}} / 当日量÷MA5 {{volume_vs_ma5}} / 当日量÷MA20 {{volume_vs_ma20}} / 近20日÷前20日 {{recent20_vs_previous20}} / 上涨日÷下跌日均量 {{up_down_volume_ratio_90d}}；MFI {{mfi14}} / CMF {{cmf20}} / OBV20 {{obv_20d_direction}}；{{price_volume_label_and_interpretation}}
```

- [ ] **Step 4: Update the Skill**

Require all held/core stocks to consume `price_volume` from report context, render the listed fields, retain `unavailable`, and apply these interpretation boundaries:

- “上涨放量” is not automatically a breakout.
- “下跌缩量” is not automatically stabilization.
- “下跌放量 + CMF<0” must be described as negative price-volume structure.
- H-share gaps cannot be replaced by A-share indicators.

- [ ] **Step 5: Test and commit**

Run:

```bash
.venv/bin/pytest tests/spec/test_skill_contracts.py -q
python -m src.spec check --workflow daily-report --phase preflight
```

Expected: Skill contract tests pass. The spec preflight may still report existing template-parameter/evidence injection failures; record the exact result and do not claim the generic checker passed if it did not.

```bash
git add references/templates/daily-report-v2.md .agents/skills/daily-report/SKILL.md tests/spec/test_skill_contracts.py
git commit -m "docs: require price-volume daily cards"
```

### Task 5: Generate and Verify a Complete Daily Report

**Files:**
- Modify: `tracking/daily/positions/2026-07-17.md`
- Modify: `tracking/daily/positions/2026-07-17.html`
- Modify if required: `index.html`

**Interfaces:**
- Consumes: Tasks 1–4 and the registered daily workflow.
- Produces: published seven-section report with held/core price-volume lines.

- [ ] **Step 1: Run focused and regression tests**

Run:

```bash
.venv/bin/pytest tests/test_daily_metrics.py tests/test_quant_pipeline.py tests/test_report_lib.py tests/spec/test_skill_contracts.py -q
.venv/bin/pytest tests/spec -q
git diff --check
```

Expected: all selected tests pass. Any unrelated pre-existing failure must be recorded with its failing test and left outside this change.

- [ ] **Step 2: Refresh and generate the target report**

Use the latest completed trading day available when this plan was approved, 2026-07-17:

```bash
source .venv/bin/activate
python scripts/fetch_all_daily.py
python scripts/run_quant_analysis.py --date 2026-07-17
```

Read `tracking/tracklist.json`, every applicable `position.json`, and `data/report_context.json`. Generate the seven-section Markdown so every held/core stock includes one “价量结构” line. Do not expand the full metric set for ordinary observation stocks.

- [ ] **Step 3: Verify coverage and consistency**

Run a small read-only verification that:

- builds the expected held/core code set;
- confirms every code has `price_volume` or explicit `unavailable`;
- confirms each corresponding report card includes “价量结构”;
- confirms duplicate appearances use identical numeric values.

Expected: no missing held/core cards and no cross-market substitution.

- [ ] **Step 4: Render, publish and verify**

Generate self-contained mobile HTML from the registered Markdown, update the index by full scan, then:

```bash
git add tracking/daily/positions/2026-07-17.md tracking/daily/positions/2026-07-17.html index.html
git commit -m "report: add daily price-volume cards"
git push origin main
gh run list --limit 5
RUN_ID=$(gh run list --workflow pages-build-deployment --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
python scripts/verify_scheduled_daily.py --date 2026-07-17 --url "https://t0nyma.github.io/stock-on/tracking/daily/positions/2026-07-17.html"
gh api repos/T0nyMa/stock-on/pages --jq '{status:.status,url:.html_url}'
```

Expected: push succeeds, Pages workflow concludes successfully, scheduled-report verification returns `"ok": true`, and Pages status is `built`.

- [ ] **Step 5: Final completion audit**

Run:

```bash
git status --short
git log -5 --oneline
```

Confirm task commits exist, unrelated dirty files remain untouched, and report the exact commit IDs plus any unavailable metrics or generic spec-checker limitation.
