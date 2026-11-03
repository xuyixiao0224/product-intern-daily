#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
GIT="${GIT:-git}"
DAY="$(date +%F)"
OUT="data/daily/$DAY"
mkdir -p "$OUT"

python3 scripts/collect_seed.py --mode daily --target 60 --out "$OUT/candidates.json"
python3 scripts/fetch_parallel.py "$OUT/candidates.json" "$OUT/details" 60 2
python3 scripts/ocr_covers.py --details "$OUT/details" --out "$OUT/ocr" --covers "$OUT/covers_raw"
OCR_DIR="$OUT/ocr" python3 scripts/heuristic_extract.py "$OUT/details" "$OUT/extractions.json"
python3 scripts/build_seed_report.py --details "$OUT/details" --extractions "$OUT/extractions.json" --out "$OUT/jobs.json" --covers "$OUT/covers"

python3 scripts/merge_jobs.py --base data/jobs.json --new "$OUT/jobs.json" --out data/jobs.json
python3 scripts/build_site.py data/jobs.json docs/index.html --images-dir "$OUT/covers" --site-url "https://xuyixiao0224.github.io/product-intern-daily/"
python3 scripts/generate_readme.py data/jobs.json docs/JOBS.md
python3 scripts/build_feed.py data/jobs.json docs/feed.xml "https://xuyixiao0224.github.io/product-intern-daily/"

# 只提交真实精选数据与站点；原始详情仍留在本地 data/daily
$GIT add data/jobs.json docs
$GIT commit -m "chore: daily ${DAY}" || true
$GIT push
date -Iseconds > data/.last_success
echo "daily done: $DAY"
