# Task 5 Report — Complete Daily Price-Volume Cards

## Result

- Updated the registered seven-section report for 2026-07-17.
- Added one `价量结构` line to every held/core card in sections 2 and 3.
- Reused identical registered `price_volume` values for duplicate A-share cards.
- Kept the held 02050.HK card explicitly `unavailable`; it does not borrow 002050 A-share metrics.
- Mechanically regenerated `tracking/daily/positions/2026-07-17.html` from the Markdown.
- Confirmed the full-scan index already contains the 2026-07-17 report exactly once, so `index.html` required no change.
- Added `tests/test_daily_price_volume_report.py` to verify held/core coverage, registered values, duplicate consistency, and the A/H market boundary.

## Data preparation

Network refresh was intentionally skipped because the registered database was already refreshed through 2026-07-17.

```text
PYTHONPATH=. DATABASE_PATH=/Users/majiang/Work/tools/stock-on/data/stock_analysis.db \
  /Users/majiang/Work/tools/stock-on/.venv/bin/python \
  scripts/run_quant_analysis.py --date 2026-07-17
{"stocks_written": 22, "positions": 3}
```

Generated `data/*` changes were not staged.

## Verification

```text
PYTHONPATH=. /Users/majiang/Work/tools/stock-on/.venv/bin/pytest \
  tests/test_daily_metrics.py tests/quant/test_pipeline.py \
  tests/test_report_lib.py tests/spec/test_skill_contracts.py \
  tests/test_daily_price_volume_report.py -q
34 passed in 3.07s

PYTHONPATH=. /Users/majiang/Work/tools/stock-on/.venv/bin/pytest tests/spec -q
164 passed in 7.73s

rg -c "价量结构" tracking/daily/positions/2026-07-17.md \
  tracking/daily/positions/2026-07-17.html
Markdown: 10
HTML: 10

git diff --check
exit 0
```

## Coverage

- Held cards: 601138, 600547, 02050.HK, 601899.
- Core/deep cards: 601138, 600547, 002050, 601899, 603986, 09988.
- Duplicate A-share values checked: 601138, 600547, 601899.
- Cross-market check: 02050.HK has explicit unavailable evidence and rejects the 002050 A-share line.

## Concerns and recorded limitations

- The worktree has no `.venv`; the brief's relative `.venv/bin/pytest` command failed. Tests were rerun with the main repository virtual environment and `PYTHONPATH=.`.
- The brief names `tests/test_quant_pipeline.py`, but the registered test is `tests/quant/test_pipeline.py`; the corrected path was used.
- `intraday_volume_ratio` and `obv_20d_direction` are unavailable for all covered registered snapshots.
- 02050.HK has no registered same-market price-volume snapshot; all price-volume fields remain explicit `unavailable`.
- The generic workflow completion checker requires pushed deployment evidence. Per the branch sequencing resolution, push, Pages deployment, and completion-gate verification are deferred until review and integration.
- Pre-existing generated modifications under `data/002050`, `data/600547`, `data/601138`, and `data/603986` remain untouched and unstaged.
