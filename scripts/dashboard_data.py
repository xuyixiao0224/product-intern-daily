"""Shared reporting semantics for the README, SVGs and optional HTML export."""
from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def recorded_date(job):
    """Preserve existing first-seen dates; legacy imports may use publication dates."""
    value = str(job.get("first_seen_at") or job.get("published_at") or "")
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(SHANGHAI)
        return parsed.date().isoformat()
    except ValueError:
        return date.fromisoformat(value[:10]).isoformat()


def reporting_date(jobs):
    return max((recorded_date(j) for j in jobs if recorded_date(j)), default=datetime.now(SHANGHAI).date().isoformat())


def hiring_status(job):
    if job.get("closed"):
        return "已截止"
    return "在招" if job.get("still_hiring") == "在招" else "待确认"


def build_stats(jobs, report_date=None):
    report_date = report_date or reporting_date(jobs)
    date.fromisoformat(report_date)
    source_total = len(jobs)
    later_total = sum(bool(recorded_date(j)) and recorded_date(j) > report_date for j in jobs)
    jobs = [j for j in jobs if not recorded_date(j) or recorded_date(j) <= report_date]
    groups = defaultdict(list)
    undated = 0
    for job in jobs:
        day = recorded_date(job)
        if day:
            groups[day].append(job)
        else:
            undated += 1
    rows, total = [], 0
    for day, items in sorted(groups.items()):
        total += len(items)
        rows.append({"date": day, "new": len(items), "total": total})
    new = sum(len(items) for day, items in groups.items() if day == report_date)
    return {
        "schema_version": 2,
        "generated_at": datetime.now(SHANGHAI).isoformat(timespec="seconds"),
        "report_date": report_date,
        "total": len(jobs),
        "source_total": source_total,
        "new": new,
        "previous_total": sum(len(items) for day, items in groups.items() if day < report_date),
        "later_total": later_total,
        "undated": undated,
        "active": sum(hiring_status(j) == "在招" for j in jobs),
        "uncertain": sum(hiring_status(j) == "待确认" for j in jobs),
        "closed": sum(hiring_status(j) == "已截止" for j in jobs),
        "convertible": sum(bool(j.get("convertible")) for j in jobs),
        "with_email": sum(bool(j.get("email")) for j in jobs),
        "by_date": rows,
    }


def aggregate(rows, mode):
    """Calendar weeks start Monday; never fabricate observations for missing days."""
    if mode not in ("day", "week", "month"):
        raise ValueError(mode)
    groups = {}
    for row in sorted(rows, key=lambda r: r["date"]):
        d = date.fromisoformat(row["date"])
        if mode == "week":
            start = d - timedelta(days=d.weekday())
            key = start.isoformat()
            label = f"{start:%m/%d}–{start + timedelta(days=6):%m/%d}"
        elif mode == "month":
            key = d.strftime("%Y-%m")
            label = d.strftime("%Y/%m")
        else:
            key, label = d.isoformat(), d.strftime("%m/%d")
        group = groups.setdefault(key, {"date": key, "label": label, "new": 0, "total": 0})
        group["new"] += row["new"]
        group["total"] = row["total"]
    return list(groups.values())
