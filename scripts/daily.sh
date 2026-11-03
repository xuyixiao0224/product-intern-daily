#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
GIT="${GIT:-git}"
ROOT="$(cd ../.. && pwd)"
MCP_BIN="$ROOT/work/xhs-mcp-src/xiaohongshu-mcp-patched"
if ! lsof -nP -iTCP:18060 -sTCP:LISTEN >/dev/null 2>&1; then
  (HOME="$ROOT/.xhs-home" nohup "$MCP_BIN" > /tmp/xhs-mcp-daily.log 2>&1 &)
  sleep 6
fi
DAY="$(date +%F)"
TARGET="${DAILY_TARGET:-60}"
OUT="data/daily/$DAY"
mkdir -p "$OUT"

python3 scripts/collect_seed.py --mode daily --target "$TARGET" --out "$OUT/candidates.json"
FETCH_LOG="$(mktemp)"
python3 scripts/fetch_parallel.py "$OUT/candidates.json" "$OUT/details" "$TARGET" 2 | tee "$FETCH_LOG"
LAST="$(tail -1 "$FETCH_LOG")"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print("fetch ok=%s err=%s" % (d.get("ok"), d.get("err"))); sys.exit(1 if d.get("err") else 0)' "$LAST"
rm -f "$FETCH_LOG"
python3 scripts/ocr_covers.py --details "$OUT/details" --out "$OUT/ocr" --covers "$OUT/covers_raw"
OCR_DIR="$OUT/ocr" python3 scripts/heuristic_extract.py "$OUT/details" "$OUT/extractions.json"
python3 scripts/build_seed_report.py --details "$OUT/details" --extractions "$OUT/extractions.json" --out "$OUT/jobs.json" --covers "$OUT/covers"

python3 scripts/merge_jobs.py --base data/jobs.json --new "$OUT/jobs.json" --out data/jobs.json
python3 scripts/build_site.py data/jobs.json docs/index.html --images-dir "$OUT/covers" --site-url "http://127.0.0.1:8000/"
python3 scripts/generate_readme.py data/jobs.json docs/JOBS.md
python3 scripts/build_feed.py data/jobs.json docs/feed.xml "http://127.0.0.1:8000/"

# 只提交真实精选数据与站点；原始详情仍留在本地 data/daily
if [ "${DAILY_PUSH:-1}" = "1" ]; then
  $GIT add data/jobs.json docs
  $GIT commit -m "chore: daily ${DAY}" || true
  $GIT push
fi
date -Iseconds > data/.last_success
echo "daily done: $DAY"
