#!/usr/bin/env python3
"""Aggregate historical jobs.json into data/stats.json."""
import argparse, json
from datetime import datetime
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--out", default="data/stats.json")
    ap.add_argument("--today-jobs", default="")
    args = ap.parse_args()
    data = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    by = {}
    for j in jobs:
        d = str(j.get("first_seen_at") or j.get("published_at") or "")[:10]
        if not d:
            continue
        by.setdefault(d, []).append(j)
    rows, total = [], 0
    for d in sorted(by):
        items = by[d]
        total += len(items)
        rows.append({
            "date": d,
            "new": len(items),
            "total": total,
            "active": sum(1 for x in items if x.get("still_hiring") == "在招" and not x.get("closed")),
            "convertible": sum(1 for x in items if x.get("convertible")),
            "email": sum(1 for x in items if x.get("email")),
        })
    if args.today_jobs and Path(args.today_jobs).exists():
        t=json.loads(Path(args.today_jobs).read_text(encoding='utf-8')).get('jobs',[])
        if rows: rows[-1]['new']=len(t)
    out = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "total": len(jobs),
        "active": sum(1 for x in jobs if x.get("still_hiring") == "在招" and not x.get("closed")),
        "closed": sum(1 for x in jobs if x.get("closed")),
        "convertible": sum(1 for x in jobs if x.get("convertible")),
        "with_email": sum(1 for x in jobs if x.get("email")),
        "by_date": rows,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False)[:300])


if __name__ == "__main__":
    main()
