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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--readme", default="README.md")
    args = ap.parse_args()
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))["jobs"]
    jobs = [j for j in jobs if not j.get("closed")]
    jobs.sort(key=lambda j: (bool(emails(j.get("email"))), str(j.get("published_at") or "")), reverse=True)
    lines = [START, f"## 在招岗位（{len(jobs)}）", "", "| 公司 | 岗位 | Base | 投递 | 转正 | 发布 |", "|---|---|---|---|---|---|"]
    for j in jobs:
        email = emails(j.get("email"))
        source = j.get('source_url','')
        apply_cell = f"[{email}](mailto:{email}) · [见原帖]({source})" if email else f"[见原帖]({source})"
        pos = j.get("position") or j.get("title") or "未识别"
        lines.append("| " + " | ".join([
            company_of(j),
            f"[{cell(position_of(j))}]({j.get('source_url','')})",
            cell(j.get("base_location") or j.get("location") or "待确认"),
            apply_cell,
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
