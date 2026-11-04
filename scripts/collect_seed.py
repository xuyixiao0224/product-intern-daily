#!/usr/bin/env python3
"""Collect daily candidates: 3 keywords, latest first, capped per keyword.

Note: xiaohongshu-mcp search_feeds returns the first page only (~20 notes),
so the per-keyword cap is 100 but the actual yield is usually ~20 until
search pagination is added.
"""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.mcp_client import MCPClient

KEYWORDS = ["产品实习", "产品继任", "互联网产品"]
BASES = ["", "北京", "上海", "深圳", "杭州", "广州"]
TIMES = ["一天内", "一周内", "半年内"]


def add_items(items, out, seen, meta):
    added = 0
    for it in items:
        if it.post_id in seen:
            continue
        seen.add(it.post_id)
        d = it.to_dict()
        d.update(meta)
        out.append(d)
        added += 1
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=300, help="overall cap")
    ap.add_argument("--per-keyword", type=int, default=100, help="cap per keyword")
    ap.add_argument("--mode", choices=["daily", "seed"], default="daily")
    ap.add_argument("--out", default="data/seed/candidates.json")
    ap.add_argument("--sleep", type=float, default=3.0)
    args = ap.parse_args()
    client = MCPClient()
    seen, out = set(), []

    if args.mode == "daily":
        # 只按“最新 + 一天内”抓；每个关键词单独计数，最多 100 条
        for kw in KEYWORDS:
            try:
                items = client.search(kw, limit=args.per_keyword, sort_by="最新", publish_time="一天内", note_type="图文")
            except Exception as exc:
                print(f"[err] {kw}: {exc}", file=sys.stderr)
                continue
            before = len(out)
            add_items(items, out, seen, {"query": kw, "publish_time_filter": "一天内"})
            got = len(out) - before
            print(f"[ok] {kw}: +{got} -> {len(out)} (per-keyword cap {args.per_keyword})", file=sys.stderr)
            if got < args.per_keyword:
                print(f"[cap] {kw}: got {got}/{args.per_keyword}; no more pages in the current time window", file=sys.stderr)
            if len(out) >= args.target:
                break
            time.sleep(args.sleep)
        times, bases = ["一天内"], [""]
    else:
        times, bases = TIMES, BASES
        for when in times:
            for base in bases:
                for kw in KEYWORDS:
                    q = f"{kw} {base}".strip()
                    try:
                        items = client.search(q, limit=min(args.per_keyword, 100), sort_by="最新", publish_time=when, note_type="图文")
                    except Exception as exc:
                        print(f"[err] {q} / {when}: {exc}", file=sys.stderr)
                        continue
                    add_items(items, out, seen, {"query": q, "publish_time_filter": when})
                    print(f"[ok] {q} / {when}: -> {len(out)}", file=sys.stderr)
                    if len(out) >= args.target:
                        break
                    time.sleep(args.sleep)
                if len(out) >= args.target:
                    break
            if len(out) >= args.target:
                break

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"mode": args.mode, "keywords": KEYWORDS, "bases": bases, "times": times, "per_keyword": args.per_keyword, "count": len(out), "candidates": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"count": len(out), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
