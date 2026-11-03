#!/usr/bin/env python3
"""Generate docs/JOBS.md from a jobs.json feed."""
import json, sys
from datetime import datetime
from pathlib import Path


def esc(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def main(src="data/jobs.json", out="docs/JOBS.md"):
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    active = [j for j in jobs if not j.get("closed")]
    closed = [j for j in jobs if j.get("closed")]
    today = datetime.now().astimezone().date().isoformat()
    new_today = [j for j in active if str(j.get("first_seen_at") or j.get("published_at") or "")[:10] == today]
    lines = [
        "# 岗位列表",
        "",
        f"> 自动生成，数据源 `{src}`；生成时间 {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        f"- 在库：**{len(jobs)}**",
        f"- 今日新增：**{len(new_today)}**",
        f"- 在招/待确认：**{len(active)}**",
        f"- 已截止/已招到：**{len(closed)}**",
        "",
        "> RSS: `feed.xml` · 邮件订阅: `subscribe.html`",
        "",
        "## 在招 / 待确认",
        "",
        "| 公司 | 岗位 | Base | 邮箱 | 内推码 | 转正 | 发布 | 状态 | 原帖 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for j in active:
        lines.append(
            f"| {esc(j.get('company'))} | {esc(j.get('position'))} | {esc(j.get('base_location') or j.get('location'))} | "
            f"{esc(j.get('email')) or '—'} | {esc(j.get('referral_code')) or '—'} | {'可转正' if j.get('convertible') else '日常实习'} | {esc(str(j.get('published_at',''))[:10])} | "
            f"{esc(j.get('still_hiring'))} | [link]({j.get('source_url')}) |"
        )
    lines += ["", "## 已截止 / 已招到", "", "| 公司 | 岗位 | Base | 发布 | 依据 |", "|---|---|---|---|---|"]
    for j in closed:
        lines.append(
            f"| {esc(j.get('company'))} | {esc(j.get('position'))} | {esc(j.get('base_location') or j.get('location'))} | "
            f"{esc(str(j.get('published_at',''))[:10])} | {esc(j.get('status_evidence') or j.get('excluded_reason'))} |"
        )
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "active": len(active), "closed": len(closed), "out": out}, ensure_ascii=False))


if __name__ == "__main__":
    main(*(sys.argv[1:3] or []))
