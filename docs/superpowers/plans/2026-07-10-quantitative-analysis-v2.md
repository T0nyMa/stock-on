# Quantitative Analysis V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic quantitative artifacts for technical, breadth, calibrated strategy, A/H, cross-asset, and portfolio analysis, then expose them to the daily and weekly report workflow.

**Architecture:** A new pure-computation `src/quant/` package consumes normalized pandas frames and dictionaries and returns JSON-safe dictionaries. A thin pipeline reads existing repository JSON, calls those functions, and writes versioned artifacts; report context generation consumes artifacts without recalculating metrics.

**Tech Stack:** Python 3, pandas, numpy, pytest, existing JSON/provider/report scripts.

## Global Constraints

- Do not add TA-Lib or another runtime technical-analysis dependency.
- Operational analysis uses at most 250 adjusted daily bars; calibration targets approximately 750 adjusted daily bars.
- Fewer than 250 valid history bars means `insufficient_data` and no published win rate.
- Missing and non-finite values serialize as `null`, never zero or infinity.
- Quant modules perform no network access and no file writes.
- Preserve V1/V2 providers and the seven-section daily-report structure.
- Every production behavior follows RED-GREEN-REFACTOR.

---

### Task 1: Normalized inputs and JSON-safe models

**Files:**
- Create: `src/quant/__init__.py`
- Create: `src/quant/models.py`
- Test: `tests/quant/test_models.py`

**Interfaces:**
- Produces: `normalize_bars(records: Sequence[Mapping]) -> tuple[pd.DataFrame, list[str]]`
- Produces: `json_safe(value: Any) -> Any`
- Produces: `evidence(source: str, gaps: list[str], warnings: list[str], quality_score: int) -> dict`

- [ ] **Step 1: Write failing normalization and JSON-safety tests**

```python
def test_normalize_bars_sorts_deduplicates_and_reports_warning():
    frame, warnings = normalize_bars([
        {"date": "2026-01-02", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1},
        {"date": "2026-01-01", "open": 9, "high": 10, "low": 8, "close": 9, "volume": 1},
        {"date": "2026-01-02", "open": 10, "high": 12, "low": 9, "close": 11, "volume": 2},
    ])
    assert list(frame.index.strftime("%Y-%m-%d")) == ["2026-01-01", "2026-01-02"]
    assert frame.iloc[-1]["close"] == 11
    assert warnings == ["duplicate_dates:1"]

def test_json_safe_replaces_non_finite_numbers():
    assert json_safe({"a": float("nan"), "b": float("inf")}) == {"a": None, "b": None}
```

- [ ] **Step 2: Run tests and verify missing-module failure**

Run: `pytest -q tests/quant/test_models.py`
Expected: FAIL because `src.quant.models` does not exist.

- [ ] **Step 3: Implement validation, evidence, and recursive JSON safety**

Implement strict required columns `date/open/high/low/close`, numeric coercion, invalid-row removal, stable sorting, last-observation duplicate handling, optional volume, and recursive handling for numpy/pandas scalar types.

- [ ] **Step 4: Run model tests**

Run: `pytest -q tests/quant/test_models.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/quant/__init__.py src/quant/models.py tests/quant/test_models.py
git commit -m "feat: add normalized quantitative inputs"
```

### Task 2: Core technical indicators and structure

**Files:**
- Create: `src/quant/indicators.py`
- Create: `src/quant/structure.py`
- Test: `tests/quant/test_indicators.py`
- Test: `tests/quant/test_structure.py`

**Interfaces:**
- Consumes: normalized OHLCV frame from Task 1.
- Produces: `compute_indicators(frame: pd.DataFrame) -> dict`
- Produces: `analyze_structure(frame: pd.DataFrame, indicator_frame: pd.DataFrame) -> dict`

- [ ] **Step 1: Write failing formula tests**

Test true range against `max(high-low, abs(high-prev_close), abs(low-prev_close))`; test ATR seed/rolling output, NATR, ADX/+DI/-DI bounds, Bollinger fields, OBV direction, MFI/CMF finite handling, and realized volatility on a hand-calculated series.

- [ ] **Step 2: Verify indicator tests fail for missing functions**

Run: `pytest -q tests/quant/test_indicators.py`
Expected: FAIL on imports.

- [ ] **Step 3: Implement vectorized pandas/numpy formulas**

Expose current values plus a calculation frame used by later modules. Return `None` for unmet lookbacks and finite JSON-safe values for flat series.

- [ ] **Step 4: Run indicator tests and refactor with tests green**

Run: `pytest -q tests/quant/test_indicators.py`
Expected: PASS.

- [ ] **Step 5: Write failing structure tests**

Use synthetic reversal data to assert confirmed ATR swings, clustered support/resistance, gap detection, 20-bin volume-profile totals, anchored VWAP, and suppression of setups below 1.5 reward/risk.

- [ ] **Step 6: Implement structure analysis**

Use a three-bar local pivot plus `1.0 * ATR` reversal confirmation, `0.5 * ATR` clustering, and explicit source/confidence/invalidation fields.

- [ ] **Step 7: Run indicator and structure tests**

Run: `pytest -q tests/quant/test_indicators.py tests/quant/test_structure.py`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/quant/indicators.py src/quant/structure.py tests/quant/test_indicators.py tests/quant/test_structure.py
git commit -m "feat: add technical metrics and price structure"
```

### Task 3: Relative strength and multi-timeframe analysis

**Files:**
- Create: `src/quant/relative.py`
- Create: `src/quant/timeframes.py`
- Test: `tests/quant/test_relative.py`
- Test: `tests/quant/test_timeframes.py`

**Interfaces:**
- Produces: `relative_strength(stock, benchmark, sector=None, windows=(5,20,60)) -> dict`
- Produces: `rank_relative_strength(values: Mapping[str, float]) -> dict[str, float]`
- Produces: `resample_ohlcv(frame, rule: Literal["W","ME"]) -> pd.DataFrame`
- Produces: `multi_timeframe_state(frame) -> dict`

- [ ] **Step 1: Write failing aligned-return, beta, correlation, and percentile-rank tests**
- [ ] **Step 2: Run relative tests and verify failure**

Run: `pytest -q tests/quant/test_relative.py`
Expected: FAIL on imports.

- [ ] **Step 3: Implement date-aligned benchmark and sector analysis**

Require at least `window + 1` aligned closes. Publish availability independently for benchmark and sector.

- [ ] **Step 4: Write failing weekly/monthly aggregation and conflict tests**
- [ ] **Step 5: Implement no-look-ahead OHLCV aggregation and timeframe trend state**

Trend state uses close versus MA20, MA20 slope, and ADX when available; partial current periods are labeled partial.

- [ ] **Step 6: Run both test files**

Run: `pytest -q tests/quant/test_relative.py tests/quant/test_timeframes.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/quant/relative.py src/quant/timeframes.py tests/quant/test_relative.py tests/quant/test_timeframes.py
git commit -m "feat: add relative strength and timeframe analysis"
```

### Task 4: Market breadth and quantitative regime

**Files:**
- Create: `src/quant/breadth.py`
- Test: `tests/quant/test_breadth.py`
- Modify: `scripts/fetch_all_daily.py`

**Interfaces:**
- Produces: `compute_breadth(quotes, histories, previous_ad_line=0.0, index_history=None) -> dict`
- Produces artifact schema `data/market/market_breadth.json` through orchestration only.

- [ ] **Step 1: Write failing participation, limit, new-high/low, MA breadth, AD-line, and divergence tests**
- [ ] **Step 2: Run breadth tests and verify failure**

Run: `pytest -q tests/quant/test_breadth.py`
Expected: FAIL on imports.

- [ ] **Step 3: Implement breadth dimensions with independent availability**

Support A-share board-specific limit percentages through explicit quote inputs; do not infer broken-limit counts when intraday high data is absent.

- [ ] **Step 4: Add deterministic regime scoring**

Score breadth, index trend, realized volatility, and liquidity independently; compute the composite only from available weighted dimensions and publish coverage.

- [ ] **Step 5: Integrate breadth inputs into daily snapshot without network logic in `src/quant`**
- [ ] **Step 6: Run breadth and existing regime tests**

Run: `pytest -q tests/quant/test_breadth.py tests/test_regime_detection.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/quant/breadth.py tests/quant/test_breadth.py scripts/fetch_all_daily.py
git commit -m "feat: add market breadth and regime evidence"
```

### Task 5: Standard strategy contract and event-study calibration

**Files:**
- Create: `src/quant/strategy.py`
- Create: `src/quant/backtest.py`
- Test: `tests/quant/test_strategy.py`
- Test: `tests/quant/test_backtest.py`

**Interfaces:**
- Produces dataclass `StrategyResult` with `to_dict()` and the contract from the design.
- Produces: `calibrate_strategy(frame, signal_fn, regime_fn=None, horizons=(1,3,5,10,20), min_history=250) -> dict`

- [ ] **Step 1: Write failing contract validation tests**

Assert allowed signals, score/confidence bounds, actionable-signal invalidation requirement, risk/reward calculation, and unavailable calibration representation.

- [ ] **Step 2: Implement the immutable strategy result contract**
- [ ] **Step 3: Write failing synthetic backtest tests**

Assert no look-ahead, horizon returns, MAE/MFE, cooldown deduplication, regime segmentation, low-confidence event count, and no win rate below 250 source bars.

- [ ] **Step 4: Implement the event-study calibrator**
- [ ] **Step 5: Run both test files**

Run: `pytest -q tests/quant/test_strategy.py tests/quant/test_backtest.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/quant/strategy.py src/quant/backtest.py tests/quant/test_strategy.py tests/quant/test_backtest.py
git commit -m "feat: standardize and calibrate strategy signals"
```

### Task 6: A/H and cross-asset analytics

**Files:**
- Create: `src/quant/cross_market.py`
- Create: `src/quant/cross_asset.py`
- Test: `tests/quant/test_cross_market.py`
- Test: `tests/quant/test_cross_asset.py`

**Interfaces:**
- Produces: `analyze_ah_pair(a_prices, h_prices, fx_rates, as_of, max_fx_age_days=3) -> dict`
- Produces: `analyze_relationship(stock_prices, driver_prices, windows=(20,60), max_lag=5) -> dict`

- [ ] **Step 1: Write failing FX conversion, stale rejection, premium percentile/Z-score, liquidity, and lead/lag tests**
- [ ] **Step 2: Implement A/H analysis with formula inputs in output**
- [ ] **Step 3: Write failing rolling correlation, beta, lag-sign, and standardized-residual tests**
- [ ] **Step 4: Implement cross-asset alignment without long-closure forward fills**
- [ ] **Step 5: Run both test files**

Run: `pytest -q tests/quant/test_cross_market.py tests/quant/test_cross_asset.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/quant/cross_market.py src/quant/cross_asset.py tests/quant/test_cross_market.py tests/quant/test_cross_asset.py
git commit -m "feat: add cross-market and cross-asset analytics"
```

### Task 7: Portfolio technical risk

**Files:**
- Create: `src/quant/portfolio.py`
- Test: `tests/quant/test_portfolio.py`

**Interfaces:**
- Produces: `analyze_portfolio(positions, return_series, annualization=252, var_level=0.95) -> dict`

- [ ] **Step 1: Write failing weights, PnL, correlation, volatility, component-risk, drawdown, historical-VaR, concentration, and stop-stress tests**
- [ ] **Step 2: Verify failure on missing module**

Run: `pytest -q tests/quant/test_portfolio.py`
Expected: FAIL on import.

- [ ] **Step 3: Implement portfolio calculations with incomplete-asset disclosure**

Component risk contributions must sum to portfolio volatility within numerical tolerance when covariance is available.

- [ ] **Step 4: Run portfolio tests**

Run: `pytest -q tests/quant/test_portfolio.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/quant/portfolio.py tests/quant/test_portfolio.py
git commit -m "feat: add portfolio technical risk"
```

### Task 8: Artifact pipeline and deterministic report context

**Files:**
- Create: `src/quant/pipeline.py`
- Create: `src/quant/report_context.py`
- Create: `scripts/run_quant_analysis.py`
- Test: `tests/quant/test_pipeline.py`
- Test: `tests/quant/test_report_context.py`
- Modify: `scripts/fetch_all_daily.py`
- Modify: `src/indicators.py`

**Interfaces:**
- Produces: `build_stock_snapshot(...) -> dict`
- Produces: `build_report_context(snapshot, breadth, cross_market, portfolio) -> dict`
- CLI: `python scripts/run_quant_analysis.py [--date YYYY-MM-DD] [--codes ...]`

- [ ] **Step 1: Write failing golden-schema integration test using offline fixtures**

Assert `schema_version == "2.0"`, required sections, evidence propagation, JSON-safe output, and deterministic equality across repeated runs with fixed `as_of`.

- [ ] **Step 2: Implement pure snapshot and report-context builders**
- [ ] **Step 3: Implement thin repository I/O CLI**

Read existing `data/{code}/kline.json`, quote/indicator files, tracking list, positions, benchmarks, FX and driver series when present. Write the five specified artifact types atomically.

- [ ] **Step 4: Expand operational history requests from 60 to 250 bars and expose optional 750-bar calibration fetch**
- [ ] **Step 5: Run pipeline tests plus existing indicator tests**

Run: `pytest -q tests/quant/test_pipeline.py tests/quant/test_report_context.py tests/test_indicators.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/quant/pipeline.py src/quant/report_context.py scripts/run_quant_analysis.py tests/quant/test_pipeline.py tests/quant/test_report_context.py scripts/fetch_all_daily.py src/indicators.py
git commit -m "feat: build quantitative analysis artifacts"
```

### Task 9: Daily and weekly workflow integration

**Files:**
- Modify: `.agents/skills/daily-report/SKILL.md`
- Modify: `.agents/skills/weekly-report/SKILL.md`
- Modify: `AGENTS.md`
- Modify: `references/scenarios/daily-summary.md`
- Modify: `references/scenarios/weekly-summary.md`
- Test: `tests/quant/test_report_requirements.py`

**Interfaces:**
- Consumes only generated report context fields for quantitative statements.
- Preserves the seven daily sections and existing deployment behavior.

- [ ] **Step 1: Write failing workflow-contract tests**

Assert instructions require breadth/regime, timeframe alignment, relative strength, ATR risk, entry/invalidation/target/RR, calibration status, dated FX for A/H, cross-asset evidence, portfolio risk, and explicit unavailable disclosure.

- [ ] **Step 2: Update daily workflow and templates**
- [ ] **Step 3: Update weekly workflow with real weekly indicators, breadth trend, rank changes, and prior-call verification**
- [ ] **Step 4: Run report requirements tests**

Run: `pytest -q tests/quant/test_report_requirements.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/daily-report/SKILL.md .agents/skills/weekly-report/SKILL.md AGENTS.md references/scenarios/daily-summary.md references/scenarios/weekly-summary.md tests/quant/test_report_requirements.py
git commit -m "docs: integrate quantitative evidence into reports"
```

### Task 10: Full regression and documentation

**Files:**
- Modify: `docs/design/analysis-v2.md`
- Modify: `docs/design/data-source-v2.md`
- Modify: `references/skills-index.md`
- Modify: `src/README.md`

**Interfaces:**
- Documents artifact generation, schemas, commands, limitations, and migration status.

- [ ] **Step 1: Run the entire offline suite**

Run: `pytest -q`
Expected: PASS with no network requirement.

- [ ] **Step 2: Run static repository checks**

Run: `python -m compileall -q src scripts && git diff --check`
Expected: exit 0.

- [ ] **Step 3: Run the quantitative CLI on committed/local current data without fetching**

Run: `python scripts/run_quant_analysis.py --date 2026-07-10`
Expected: creates valid versioned artifacts for stocks with sufficient local inputs and explicit gaps for the rest.

- [ ] **Step 4: Update design status and operator documentation**
- [ ] **Step 5: Re-run focused and full tests after documentation/workflow edits**

Run: `pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/design/analysis-v2.md docs/design/data-source-v2.md references/skills-index.md src/README.md
git commit -m "docs: document quantitative analysis v2"
```

## Plan self-review

- Spec coverage: all nine analysis components, five artifacts, orchestration, reports, error policy, and tests map to Tasks 1-10.
- Placeholder scan: no deferred implementation placeholders are used.
- Type consistency: normalized frames feed all pure modules; dictionaries become JSON-safe only at artifact boundaries; all dates are explicit.
- Scope isolation: every task produces an independently testable module or integration boundary.
