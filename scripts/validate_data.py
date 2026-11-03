#!/usr/bin/env python3
"""Validate a jobs.json feed without external dependencies."""
import json, sys
from pathlib import Path

REQUIRED = ["post_id", "company", "position", "published_at", "still_hiring", "source_url"]
STATUS = {"在招", "无法确认"}

def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    errors, seen_ids, seen_emails = [], set(), {}
    for i, j in enumerate(jobs):
        for k in REQUIRED:
            if not j.get(k):
                errors.append(f"[{i}] missing {k}")
        if j.get("post_id") in seen_ids:
            errors.append(f"[{i}] duplicate post_id {j.get('post_id')}")
        seen_ids.add(j.get("post_id"))
        if j.get("still_hiring") not in STATUS:
            errors.append(f"[{i}] invalid still_hiring {j.get('still_hiring')!r}")
        if not str(j.get("source_url", "")).startswith("https://"):
            errors.append(f"[{i}] source_url must be https")
        for e in str(j.get("email") or "").split(";"):
            e = e.strip().lower()
            if not e:
                continue
            if e in seen_emails and seen_emails[e] != j.get("post_id"):
                errors.append(f"[{i}] duplicate email {e} (also {seen_emails[e]})")
            seen_emails[e] = j.get("post_id")
    print(json.dumps({"jobs": len(jobs), "errors": errors[:50], "error_count": len(errors)}, ensure_ascii=False, indent=1))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "data/jobs.example.json"))
