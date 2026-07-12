#!/bin/zsh
set -eu

REPO="/Users/majiang/Work/tools/stock-on"
LOG_DIR="$REPO/logs/automation"
LOCK_DIR="$LOG_DIR/daily-report.lock"

mkdir -p "$LOG_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date '+%F %T %Z')] skipped: daily report is already running"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM

echo "[$(date '+%F %T %Z')] starting scheduled daily report"

REPORT_DATE="$(TZ=Asia/Shanghai date '+%F')"
REPORT_URL="https://t0nyma.github.io/stock-on/tracking/daily/positions/${REPORT_DATE}.html"

/usr/local/bin/codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --cd "$REPO" \
  --output-last-message "$LOG_DIR/last-message.txt" \
  '使用 $daily-report 执行登记的 daily-report 工作流。严格读取 AGENTS.md、daily-report Skill、spec/workflows/daily-report.yaml 和 references/templates/daily-report-v2.md。先刷新全部数据并运行 run_quant_analysis.py，再执行 python -m src.spec check --workflow daily-report --phase preflight；消息面优先使用 AnySearch，额度耗尽、服务失败或结果不足时才使用 EasyAnySearch，并核验交易所/公司公告。唯一 Markdown 交付物必须是 tracking/daily/positions/YYYY-MM-DD.md，禁止生成逐股日报和独立大盘 Markdown。复用 SQLite 中最新 research_summary 与 financial_collection_status，生成七章报告，更新持仓，执行 deploy，完成 Git 提交和推送，验证 GitHub Pages。最后执行 python -m src.spec check --workflow daily-report --phase completion。全程不询问用户；任何门禁、推送、部署或线上验证失败都必须以失败结束，不得声称完成。'

source "$REPO/.venv/bin/activate"
python "$REPO/scripts/verify_scheduled_daily.py" \
  --repo "$REPO" \
  --date "$REPORT_DATE" \
  --url "$REPORT_URL"

echo "[$(date '+%F %T %Z')] scheduled daily report finished"
