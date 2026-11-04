#!/usr/bin/env python3
"""Count unique pool records by first-seen date, never by daily batch size."""
import argparse
import json
from pathlib import Path
from dashboard_data import build_stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--out", default="data/stats.json")
    ap.add_argument("--report-date", default=None, help="ISO date; defaults to the latest recorded date")
    # Retain the old CLI option, but do not overwrite a cohort with batch counts.
    ap.add_argument("--today-jobs", default="", help="Compatibility option; batch size is not the number of new records")
    args = ap.parse_args()
    data = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    stats = build_stats(jobs, args.report_date)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("report_date", "new", "previous_total", "total")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
