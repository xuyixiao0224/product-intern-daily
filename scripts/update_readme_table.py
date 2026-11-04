#!/usr/bin/env python3
"""Render a SimplifyJobs-style jobs table into README.md between markers."""
import argparse, json, re
from datetime import datetime
from pathlib import Path
from dashboard_data import hiring_status, recorded_date, reporting_date

START = "<!-- JOBS:START -->"
END = "<!-- JOBS:END -->"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def flat(v):
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x).strip() for x in v if str(x).strip())
    return str(v or "").strip()


def emails(v):
    found = list(dict.fromkeys(EMAIL_RE.findall(flat(v))))
    return "; ".join(found)


KNOWN_COMPANIES = ["字节跳动", "腾讯", "百度", "阿里巴巴", "美团", "快手", "小红书", "小米", "爱奇艺", "哔哩哔哩", "网易", "京东", "滴滴", "OPPO", "科大讯飞", "航旅纵横", "中银基金"]


def cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


def company_of(j):
    name = cell(j.get("company"))
    if name and name not in ("未识别", "None"):
        return name
    text = f"{j.get('title','')} {j.get('description','')}"
    for known in KNOWN_COMPANIES:
        if known in text:
            return known
    return "公司未注明"


def position_of(j):
    pos = cell(j.get("position") or j.get("title"))
    pos = re.sub(r"^(?:(?:啦|组内直推|急招|实习招聘[丨|]?|招聘[丨|]?)\s*)+", "", pos)
    return pos.strip() or "岗位未注明"


def compact_base(job):
    value = cell(job.get("base_location") or job.get("location") or "待确认")
    if len(value) > 30:
        cities = [x.strip() for x in re.split(r"[、，,/／]", value) if x.strip()]
        return " / ".join(cities[:2]) + "等多地"
    return value


def render_table(jobs, include_date=False):
    ordered = sorted(jobs, key=lambda j: (bool(emails(j.get("email"))), str(j.get("published_at") or "")), reverse=True)
    headers = ["公司", "岗位", "Base", "投递", "状态", "转正"]
    if include_date:
        headers.append("首次记录")
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for job in ordered:
        email = emails(job.get("email"))
        source = job.get("source_url", "")
        apply_cell = f"[{email}](mailto:{email})" if email else f"[见原帖]({source})"
        row = [company_of(job), f"[{position_of(job)}]({source})", compact_base(job), apply_cell,
               hiring_status(job), "可转正" if job.get("convertible") else "日常实习"]
        if include_date:
            row.append(recorded_date(job) or "未记录")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_jobs_block(jobs, report_date=None):
    day = report_date or reporting_date(jobs)
    jobs = [j for j in jobs if not recorded_date(j) or recorded_date(j) <= day]
    current = [j for j in jobs if recorded_date(j) == day and not j.get("closed")]
    previous = [j for j in jobs if recorded_date(j) != day and not j.get("closed")]
    closed = [j for j in jobs if j.get("closed")]
    lines = [START, "## 岗位追踪", "", f"**最新一期 · {day}**　按首次记录分期，旧岗位更新不重复计入新增。", "",
             f"### 本期新增 · {len(current)}", ""]
    lines.append(render_table(current) if current else "本期暂无未截止的新增岗位。")
    lines += ["", "<details>", f"<summary>往期岗位 · {len(previous)} 条未标记截止，展开继续找</summary>", "",
              "此前收录、尚未标记截止的岗位。状态为「待确认」时，请先向招聘方核实。", "",
              render_table(previous, include_date=True) if previous else "暂无往期岗位。", "", "</details>"]
    if closed:
        lines += ["", "<details>", f"<summary>已截止归档 · {len(closed)} 条</summary>", "", render_table(closed, include_date=True), "", "</details>"]
    current_closed = sum(recorded_date(j) == day for j in closed)
    if current_closed:
        lines += ["", f"本期另有 {current_closed} 条已截止，保留在归档与收录统计中。"]
    lines += [END]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json", help="The full historical pool, not a daily batch")
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--report-date", default=None)
    args = ap.parse_args()
    data = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    block = render_jobs_block(jobs, args.report_date)
    readme = Path(args.readme)
    text = readme.read_text(encoding="utf-8")
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = text.replace("## 快速开始", block + "\n\n## 快速开始", 1)
    # Keep the jump link stable when daily counts change.
    text = re.sub(r"#在招岗位[0-9]*", "#岗位追踪", text)
    readme.write_text(text, encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "readme": str(readme)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
