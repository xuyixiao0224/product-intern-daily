#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

on_error() {
  local code=$?
  local msg="daily failed at line ${LINENO}: ${BASH_COMMAND}"
  mkdir -p data
  printf '%s\n%s\n' "$(date -Iseconds)" "$msg" > data/.last_error
  echo "$msg" >&2
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"${msg//\"/}\" with title \"产品实习日报失败\"" >/dev/null 2>&1 || true
  fi
  if [ -n "${DAILY_ALERT_WEBHOOK:-}" ]; then
    curl -sS --max-time 10 -X POST "$DAILY_ALERT_WEBHOOK" -H 'Content-Type: application/json' \
      -d "{\"text\":\"产品实习日报失败: ${msg//\"/}\"}" >/dev/null 2>&1 || true
  fi
  exit "$code"
}
trap on_error ERR
GIT="${GIT:-git}"
ROOT="$(cd ../.. && pwd)"
MCP_BIN="$ROOT/work/xhs-mcp-src/xiaohongshu-mcp-patched"
if ! lsof -nP -iTCP:18060 -sTCP:LISTEN >/dev/null 2>&1; then
  (HOME="$ROOT/.xhs-home" nohup "$MCP_BIN" > /tmp/xhs-mcp-daily.log 2>&1 &)
  sleep 6
fi
DAY="$(date +%F)"
TARGET="${DAILY_TARGET:-300}"
PER_KEYWORD="${DAILY_PER_KEYWORD:-100}"
OUT="data/daily/$DAY"
mkdir -p "$OUT"

# 19:00 跑采集
python3 scripts/collect_seed.py --mode daily --target "$TARGET" --per-keyword "$PER_KEYWORD" --out "$OUT/candidates.json"
FETCH_LOG="$(mktemp)"
python3 scripts/fetch_parallel.py "$OUT/candidates.json" "$OUT/details" "$TARGET" 2 | tee "$FETCH_LOG"
LAST="$(tail -1 "$FETCH_LOG")"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("fetch ok=%s err=%s" % (d.get("ok"), d.get("err"))); sys.exit(1 if d.get("err") else 0)' "$LAST"
rm -f "$FETCH_LOG"
OCR_PY=".venv-ocr/bin/python"
[ -x "$OCR_PY" ] || OCR_PY="python3"
OCR_LOG="$(mktemp)"
"$OCR_PY" scripts/ocr_covers.py --details "$OUT/details" --out "$OUT/ocr" --covers "$OUT/covers_raw" | tee "$OCR_LOG"
OCR_LAST="$(tail -1 "$OCR_LOG")"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("ocr ok=%s err=%s" % (d.get("ok"), d.get("err"))); sys.exit(1 if d.get("err") else 0)' "$OCR_LAST"
rm -f "$OCR_LOG"
OCR_DIR="$OUT/ocr" python3 scripts/heuristic_extract.py "$OUT/details" "$OUT/extractions.json"
python3 scripts/build_seed_report.py --details "$OUT/details" --extractions "$OUT/extractions.json" --out "$OUT/jobs.json" --covers "$OUT/covers"

# 等到 20:00 再发布（README 表格 + 邮件 + push）
python3 - <<'PY'
from datetime import datetime
import time
now = datetime.now()
target = now.replace(hour=20, minute=0, second=0, microsecond=0)
if target > now:
    time.sleep((target - now).total_seconds())
PY

python3 scripts/merge_jobs.py --base data/jobs.json --new "$OUT/jobs.json" --out data/jobs.json
python3 scripts/build_site.py data/jobs.json docs/index.html --images-dir "$OUT/covers" --site-url "http://127.0.0.1:8000/"
python3 scripts/generate_readme.py data/jobs.json docs/JOBS.md
python3 scripts/build_feed.py data/jobs.json docs/feed.xml "http://127.0.0.1:8000/"
python3 scripts/update_readme_table.py --jobs data/jobs.json --readme README.md

# 发送今日邮件（Buttondown）
if [ -f .secrets/buttondown.key ]; then
  export BUTTONDOWN_API_KEY="$(cat .secrets/buttondown.key)"
  python3 scripts/send_digest.py --jobs data/jobs.json --since 1d --provider buttondown
fi

if [ "${DAILY_PUSH:-1}" = "1" ]; then
  $GIT add README.md data/jobs.json docs
  $GIT commit -m "chore: daily ${DAY}" || true
  $GIT push
fi
date -Iseconds > data/.last_success
rm -f data/.last_error
echo "daily done: $DAY"
