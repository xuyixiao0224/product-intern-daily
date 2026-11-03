#!/usr/bin/env python3
"""Merge daily jobs into cumulative jobs.json, email-first dedup."""
import argparse, json
from pathlib import Path


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="data/jobs.json")
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", default="data/jobs.json")
    args = ap.parse_args()
    merged = {}
    for job in load(Path(args.base)) + load(Path(args.new)):
        k = key(job)
        if not k or k == "note:":
            continue
        if k not in merged:
            merged[k] = job
        else:
            # prefer 在招 / newer first_seen
            old = merged[k]
            old_score = (old.get("still_hiring") == "在招", str(old.get("first_seen_at") or ""))
            new_score = (job.get("still_hiring") == "在招", str(job.get("first_seen_at") or ""))
            if new_score >= old_score:
                merged[k] = {**old, **job, "first_seen_at": old.get("first_seen_at") or job.get("first_seen_at")}
    jobs = sorted(merged.values(), key=lambda j: str(j.get("published_at") or ""), reverse=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"count": len(jobs), "jobs": jobs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
