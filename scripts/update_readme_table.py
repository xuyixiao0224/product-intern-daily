#!/usr/bin/env python3
"""Render a SimplifyJobs-style jobs table into README.md between markers."""
import argparse, json, re
from datetime import datetime
from pathlib import Path

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


def cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--readme", default="README.md")
    args = ap.parse_args()
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))["jobs"]
    jobs = [j for j in jobs if not j.get("closed")]
    jobs.sort(key=lambda j: (bool(emails(j.get("email"))), str(j.get("published_at") or "")), reverse=True)
    lines = [START, f"## 在招岗位（{len(jobs)}）", "", f"> 最近更新：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')} · 只列产品实习；投递前请核实身份。", "", "| 公司 | 岗位 | Base | 投递 | 状态 | 转正 | 发布 |", "|---|---|---|---|---|---|---|"]
    for j in jobs:
        email = emails(j.get("email"))
        apply_cell = f"[{email}](mailto:{email})" if email else f"[见原帖]({j.get('source_url','')})"
        pos = j.get("position") or j.get("title") or "未识别"
        lines.append("| " + " | ".join([
            cell(j.get("company") or "未识别"),
            f"[{cell(pos)}]({j.get('source_url','')})",
            cell(j.get("base_location") or j.get("location") or "待确认"),
            apply_cell,
            cell(j.get("still_hiring") or "无法确认"),
            "可转正" if j.get("convertible") else "日常实习",
            cell(str(j.get("published_at") or "")[:10]),
        ]) + " |")
    lines += [END]
    block = "\n".join(lines)
    readme = Path(args.readme)
    text = readme.read_text(encoding="utf-8")
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
    else:
        text = text.replace("## 快速开始", block + "\n\n## 快速开始", 1)
    readme.write_text(text, encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "readme": str(readme)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
