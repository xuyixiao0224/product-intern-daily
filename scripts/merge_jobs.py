#!/usr/bin/env python3
"""Merge daily jobs into cumulative jobs.json, email-first dedup."""
import argparse, json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


def load(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("jobs", []) if isinstance(data, dict) else data


def key(job):
    email = str(job.get("email") or "").split(";")[0].strip().lower()
    if email:
        return "email:" + email
    return "note:" + str(job.get("post_id") or "")


def merge_records(base_jobs, incoming_jobs, collected_at=None):
    # Existing dates are immutable. New imports are first seen at collection time,
    # not at the original post's publication time.
    collected_at = collected_at or datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    merged = {key(j): dict(j) for j in base_jobs if key(j) != "note:"}
    for job in incoming_jobs:
        k = key(job)
        if k == "note:":
            continue
        if k not in merged:
            merged[k] = {**job, "first_seen_at": collected_at}
            continue
        old = merged[k]
        old_score = (old.get("still_hiring") == "在招", str(old.get("first_seen_at") or ""))
        new_score = (job.get("still_hiring") == "在招", str(job.get("first_seen_at") or ""))
        if new_score >= old_score or job.get("closed"):
            merged[k] = {**old, **job, "first_seen_at": old.get("first_seen_at") or old.get("published_at") or collected_at}
    return sorted(merged.values(), key=lambda j: str(j.get("published_at") or ""), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="data/jobs.json")
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", default="data/jobs.json")
    args = ap.parse_args()
    jobs = merge_records(load(Path(args.base)), load(Path(args.new)))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"count": len(jobs), "jobs": jobs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
