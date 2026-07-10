# Quantitative Analysis V2 Design

## Goal

Build a deterministic, auditable quantitative-analysis layer for Stock-On that covers technical indicators, market breadth, multi-timeframe and relative-strength analysis, calibrated strategy evaluation, A/H and cross-asset analysis, and portfolio risk. Python computes every number; Codex explains the structured evidence without inventing or recalculating values.

## Scope and constraints

- Implement the complete analysis upgrade identified from the 2026-07-10 daily report, weekly report, and V2 design documents.
- Use the existing Python stack and `pandas`/`numpy`; do not add TA-Lib or another technical-analysis dependency.
- Daily analysis uses up to 250 adjusted daily bars. Strategy calibration uses three years, approximately 750 adjusted daily bars.
- A-share and H-share history uses forward-adjusted prices where the provider supports it.
- A backtest with fewer than 250 valid bars is `insufficient_data` and must not publish a win rate.
- Missing data produces explicit availability and gap fields. It must never be converted to zero or inferred by the report writer.
- Existing V1/V2 provider paths remain usable while the new analysis layer is introduced.
- Preserve the seven-section daily-report structure and existing tracking data.
- Avoid automatic live trading. Outputs are decision support only.

## Selected architecture

Add a focused `src/quant/` package alongside the existing analyzer. The package accepts normalized bar and snapshot data and emits deterministic JSON artifacts. Existing scripts orchestrate these components and remain responsible for file I/O.

```text
providers / existing JSON
        |
        v
src/quant normalized inputs
        |
        +-- indicators      ATR, NATR, ADX/DMI, OBV, MFI, CMF, bands, AVWAP
        +-- structure       swings, supports/resistances, gaps, volume profile
        +-- relative        benchmark/sector relative strength and beta
        +-- timeframes      daily/weekly/monthly aggregation and conflicts
        +-- breadth         participation, limits, highs/lows, AD line
        +-- strategy        standardized setups and invalidation
        +-- backtest        walk-forward outcome calibration
        +-- cross_market    FX-normalized A/H premium and lead/lag
        +-- cross_asset     rolling correlation and lag relationships
        +-- portfolio       exposure, correlation, drawdown, risk contribution
        |
        v
technical_snapshot.json / market_breadth.json / strategy_stats.json
cross_market.json / portfolio_risk.json
        |
        v
deterministic report context -> Codex narrative -> daily/weekly report
```

The package does not fetch network data and does not write files. This keeps calculations reproducible and unit-testable.

## Components

### 1. Core technical metrics

Compute from normalized OHLCV bars:

- True Range, ATR(14), NATR(14), 20/60-day realized volatility.
- ADX(14), +DI and -DI for trend strength and direction.
- Bollinger Bands(20, 2), bandwidth, and percent-B.
- OBV, MFI(14), CMF(20), and price-volume divergence flags.
- Anchored VWAP from the latest confirmed 60-day swing low or swing high.
- Existing MA, MACD, RSI, BIAS, and volume-ratio values remain available.

All rolling metrics publish `null` until their lookback is satisfied. Division-by-zero and flat-price periods return a neutral or unavailable state, never infinity.

### 2. Price structure and risk levels

Use an ATR-aware swing algorithm:

- A confirmed swing requires a local pivot and a reversal of at least `1.0 * ATR(14)`.
- Cluster nearby pivots within `0.5 * ATR(14)` to form support and resistance zones.
- Record unfilled price gaps and whether price is above or below them.
- Build a 20-bin close-location volume profile from the available daily bars.
- Generate entry, invalidation, and target zones only when structure supports a minimum 1.5 reward/risk ratio.

Every level includes its source, confidence inputs, and invalidation rule.

### 3. Relative strength and multi-timeframe state

For each stock:

- Calculate 5/20/60-day total return relative to its benchmark and sector proxy.
- Calculate 20/60-day beta and correlation when aligned observations are sufficient.
- Rank relative strength within the tracked universe from 0 to 100.
- Aggregate daily bars into weekly and monthly OHLCV without look-ahead.
- Determine trend state independently for daily, weekly, and monthly periods.
- Emit `aligned_bullish`, `aligned_bearish`, or `conflicted` with a list of conflicts.

Benchmark mapping is explicit by market and board. Missing sector history leaves sector-relative fields unavailable while preserving benchmark-relative analysis.

### 4. Market breadth and regime

Create a daily breadth snapshot containing:

- Advancers, decliners, unchanged, and advance ratio.
- Advancing and declining turnover where available.
- Limit-up, limit-down, broken-limit counts, and broken-limit rate.
- 20-day and 60-day new highs and new lows.
- Percentage above MA20 and MA60.
- Cumulative advance-decline line with a persisted prior value.
- Breadth versus index divergence.
- Total turnover versus 5/20-day averages.

Market regime combines breadth, index trend, volatility, and liquidity. Each dimension retains its own score and availability so partial data lowers confidence rather than silently changing the meaning of the composite score.

### 5. Standard strategy contract

Every strategy produces the same schema:

```json
{
  "strategy": "volume_breakout",
  "signal": "buy",
  "score": 68,
  "confidence": 0.72,
  "setup_type": "trend_continuation",
  "horizon_days": [5, 10],
  "entry_zone": [24.20, 24.80],
  "invalidation": 23.60,
  "targets": [26.50, 27.20],
  "risk_reward": 2.10,
  "evidence": [],
  "risk_flags": [],
  "calibration": {
    "status": "available",
    "sample_size": 64,
    "win_rate": 0.61,
    "expected_return": 0.034
  }
}
```

Scores represent setup quality, not predicted return. Confidence incorporates evidence quality, timeframe agreement, and historical calibration. A setup without a defensible invalidation level cannot emit `buy` or `sell`.

### 6. Backtest and calibration

Use a deterministic event-study backtester rather than a portfolio simulator for initial calibration:

- Evaluate signals at 1, 3, 5, 10, and 20 trading-day horizons.
- Calculate win rate, mean and median return, expected return, MAE, MFE, payoff ratio, and sample size.
- Segment results by strategy and market regime.
- Prevent look-ahead by computing each signal only from bars available at that timestamp.
- Deduplicate overlapping signals from the same strategy using a configurable cooldown equal to the evaluation horizon.
- Mark results with fewer than 30 signal events as low confidence.
- Refuse to publish any win rate when source history has fewer than 250 valid bars.

Calibration artifacts include input date range, price-adjustment type, code version, parameters, and generation timestamp.

### 7. A/H cross-market analysis

For paired listings:

- Convert H-share prices using dated HKD/CNY FX data before computing premium.
- Store the raw prices, FX rate, converted prices, and formula inputs.
- Calculate current premium, 20/60-day mean, standard deviation, percentile, and Z-score.
- Compare turnover, volume, and free-float data when available.
- Calculate 20/60-day return correlation and one-to-five-day lead/lag correlations.
- Flag low-liquidity conclusions as low confidence.

No A/H premium is published when the FX date is stale or unavailable.

### 8. Cross-asset relationships

Define explicit stock-to-driver mappings, initially including gold miners to COMEX gold and SGE gold. For each relationship:

- Align trading dates without forward-filling across long market closures.
- Calculate 20/60-day rolling correlation and beta.
- Test lead/lag correlations from -5 to +5 trading days.
- Quantify current divergence as a standardized residual when sufficient observations exist.
- Report the sample range and observation count.

Narrative statements such as “gold supports the stock” must reference these metrics or be labeled qualitative.

### 9. Portfolio technical risk

For current positions:

- Calculate position value, weight, unrealized return, and stop-distance risk.
- Produce 20/60-day return-correlation matrices.
- Calculate annualized portfolio volatility and marginal/component risk contribution.
- Calculate historical maximum drawdown and 95% one-day historical VaR, clearly labeled as historical estimates.
- Aggregate market, sector, and theme concentration.
- Run stop-loss stress showing cash loss if all active invalidation levels trigger.

Unavailable prices, FX, or insufficient return histories exclude the affected metric and lower portfolio evidence quality; they do not become zero-risk assets.

## Artifact schemas

### Per-stock `data/{code}/technical_snapshot.json`

Top-level sections are `identity`, `as_of`, `evidence`, `indicators`, `structure`, `relative_strength`, `timeframes`, `setups`, and `risk_summary`.

### Market `data/market/market_breadth.json`

Contains `as_of`, `universe`, `evidence`, `participation`, `limits`, `new_highs_lows`, `moving_average_breadth`, `liquidity`, `divergences`, and `regime`.

### Calibration `data/{code}/strategy_stats.json`

Contains `as_of`, `history`, `parameters`, and results grouped by strategy, regime, and horizon.

### Cross-market `data/{code}/cross_market.json`

Contains `pair`, `fx`, `premium`, `liquidity`, `correlation`, `lead_lag`, and `evidence`.

### Portfolio `data/portfolio_risk.json`

Contains `as_of`, `positions`, `exposures`, `correlation`, `volatility`, `drawdown`, `var`, `stop_stress`, and `evidence`.

JSON serialization converts non-finite numbers to `null`. Each artifact has a `schema_version` beginning at `2.0`.

## Orchestration and reports

Extend the daily pipeline in this order:

1. Fetch 250-bar operational histories, benchmark/sector histories, market breadth inputs, FX, and configured cross-asset series.
2. Compute per-stock technical snapshots.
3. Compute market breadth and regime.
4. Compute A/H, cross-asset, and portfolio artifacts.
5. Refresh three-year strategy calibration only when history or strategy code changed; reuse a dated cache otherwise.
6. Build a deterministic report context JSON.
7. Generate the existing seven-section daily report and weekly report from that context.

Daily reports add compact fields rather than new top-level chapters: evidence quality, breadth/regime, multi-timeframe state, relative strength, ATR risk, setup invalidation, calibrated statistics, A/H premium context, and portfolio risk. Weekly reports add genuine weekly indicators, breadth trend, relative-strength rank changes, and prior-call verification.

## Error handling and evidence policy

- Every computation accepts explicit `as_of` dates and validates sorted, unique bars.
- Duplicate dates keep the last provider observation and add an evidence warning.
- A missing required OHLC field invalidates that row; a missing volume invalidates volume indicators only.
- Stale thresholds are market-aware and recorded in the artifact.
- Provider failures remain provider concerns; quantitative modules receive data plus evidence metadata.
- Reports must use `unavailable` language for missing fields and must not downgrade `unavailable` to a neutral score.
- Contradictory timeframes or strategies are preserved as conflicts rather than averaged away.

## Testing strategy

Use test-first development for every production behavior.

- Unit tests use small hand-calculated OHLCV fixtures for indicator formulas and boundary behavior.
- Property-style tests verify finite output, stable sorting, scale invariance where applicable, and no future-data leakage.
- Golden-schema tests validate every JSON artifact and `null` handling.
- Backtest tests use synthetic price series with known signal timestamps and outcomes.
- A/H tests verify FX conversion, stale-FX rejection, percentile, Z-score, and lead/lag direction.
- Portfolio tests verify weights, covariance risk decomposition, drawdown, VaR, and stop stress.
- Integration tests run the quantitative pipeline on committed fixtures without network access.
- Report tests confirm that required evidence fields appear and unavailable data is disclosed.

## Delivery sequence

1. Shared models, validation, and core indicators.
2. Structure, relative strength, and multi-timeframe analysis.
3. Market breadth and regime integration.
4. Standard strategy contract and event-study calibration.
5. A/H and cross-asset analysis.
6. Portfolio risk.
7. Pipeline orchestration and deterministic context.
8. Daily/weekly report integration, documentation, and regression verification.

Each sequence produces a usable artifact and remains compatible with the prior report flow until final integration.

## Success criteria

- All new metrics are deterministically reproducible from committed fixtures.
- No new runtime dependency beyond the existing Python stack is introduced.
- All five structured artifacts validate and contain evidence metadata.
- No strategy win rate appears with fewer than 250 source bars.
- No A/H premium appears without dated FX conversion.
- Every actionable setup contains horizon, entry, invalidation, target, and risk/reward.
- Daily and weekly reports consume generated values without independently calculating them.
- Existing indicator and regime tests continue to pass.
- The complete offline test suite passes without network access.
