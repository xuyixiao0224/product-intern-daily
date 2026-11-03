#!/usr/bin/env python3
"""Search 3 core keywords across base/time slices (XHS caps one query at ~20)."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.mcp_client import MCPClient

KEYWORDS = ["产品实习", "产品继任", "互联网产品"]
BASES = ["", "北京", "上海", "深圳", "杭州", "广州"]
TIMES = ["一天内", "一周内", "半年内"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=60)
    ap.add_argument("--mode", choices=["daily", "seed"], default="daily")
    ap.add_argument("--out", default="data/seed/candidates.json")
    ap.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()
    client = MCPClient()
    seen, out = set(), []
    times = ["一天内"] if args.mode == "daily" else TIMES
    bases = [""] if args.mode == "daily" else BASES
    for ti, when in enumerate(times):
        for base in bases:
            for ki, kw in enumerate(KEYWORDS):
                q = f"{kw} {base}".strip()
                try:
                    items = client.search(q, limit=20, sort_by="最新", publish_time=when, note_type="图文")
                except Exception as exc:
                    print(f"[err] {q} / {when}: {exc}", file=sys.stderr)
                    continue
                for it in items:
                    if it.post_id in seen:
                        continue
                    seen.add(it.post_id)
                    d = it.to_dict(); d["query"] = q; d["publish_time_filter"] = when
                    out.append(d)
                print(f"[ok] {q} / {when}: +{len(items)} -> {len(out)}", file=sys.stderr)
                if len(out) >= args.target:
                    break
                time.sleep(args.sleep)
            if len(out) >= args.target:
                break
        if len(out) >= args.target:
            break
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"mode": args.mode, "keywords": KEYWORDS, "bases": bases, "times": times, "count": len(out), "candidates": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"count": len(out), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
