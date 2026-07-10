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

/usr/local/bin/codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --cd "$REPO" \
  --output-last-message "$LOG_DIR/last-message.txt" \
  '使用 $daily-report 生成今日股票日报。严格读取 AGENTS.md、daily-report Skill 和 references/templates/daily-report-v2.md；刷新全部数据，消息面使用 easy_anysearch_skill 后核验交易所/公司公告，完成七章报告、HTML、Git提交、推送和 GitHub Pages 发布。全程不询问用户，自主处理可恢复错误；若最终失败，在最终消息写明阶段、原因和未完成项。'

echo "[$(date '+%F %T %Z')] scheduled daily report finished"
