#!/usr/bin/env python3
"""Render (and optionally send) the daily product-internship digest.

Plain Markdown body, no HTML. Table mirrors the README job table.

  python scripts/send_digest.py --jobs data/jobs.json --since 1d --dry-run
  BUTTONDOWN_API_KEY=... python scripts/send_digest.py --jobs data/jobs.json --since 1d --provider buttondown
"""
import argparse, json, os, re, sys, urllib.request
from datetime import datetime, timedelta
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def emails(value):
    text = " ; ".join(value) if isinstance(value, (list, tuple)) else str(value or "")
    found = list(dict.fromkeys(EMAIL_RE.findall(text)))
    return "; ".join(found) if found else text


def cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


def load_jobs(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("jobs", []) if isinstance(data, dict) else data


def select(jobs, since, limit):
    if since:
        cutoff = since
        if since.endswith("d") and since[:-1].isdigit():
            cutoff = (datetime.now().astimezone() - timedelta(days=int(since[:-1]))).isoformat()
        jobs = [j for j in jobs if str(j.get("published_at", "")) >= cutoff]
    jobs = [j for j in jobs if not j.get("closed")]
    jobs.sort(key=lambda j: str(j.get("published_at", "")), reverse=True)
    return jobs[:limit]


def render(jobs):
    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    lines = [
        f"# 产品实习日报 · {today}",
        "",
        f"今日新增 **{len(jobs)}** 条产品实习。免费订阅，不卖数据。",
        "",
        "| 公司 | 岗位 | Base | 投递 | 状态 | 转正 |",
        "|---|---|---|---|---|---|",
    ]
    for j in jobs:
        lines.append("| " + " | ".join([
            cell(j.get("company") or "未识别"),
            cell(j.get("position") or j.get("title") or "未识别"),
            cell(j.get("base_location") or j.get("location") or "待确认"),
            emails(j.get("email")) or f"[见原帖]({j.get('source_url','')})",
            cell(j.get("still_hiring") or "无法确认"),
            "可转正" if j.get("convertible") else "日常实习",
        ]) + " |")
    lines += ["", "原帖：", ""]
    for j in jobs:
        lines.append(f"- {cell(j.get('company') or '未识别')} · {cell(j.get('position') or j.get('title'))}：{j.get('source_url','')}")
    lines += ["", "投递前请核实身份。想删除自己的帖子/邮箱，请在 GitHub 仓库开 Issue。", ""]
    body = "\n".join(lines)
    subject = f"产品实习日报 · {today}（新增 {len(jobs)} 条）"
    return subject, body


def post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode()[:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--since", default="1d", help="1d/7d or ISO date")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--provider", choices=["resend", "webhook", "buttondown"], default="")
    ap.add_argument("--to", default="", help="test recipient for Resend")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    jobs = select(load_jobs(args.jobs), args.since, args.limit)
    subject, body = render(jobs)
    out = Path("exports"); out.mkdir(exist_ok=True)
    (out / "digest.md").write_text(body, encoding="utf-8")
    if args.dry_run or not args.provider:
        print(json.dumps({"jobs": len(jobs), "dry_run": True, "file": "exports/digest.md"}, ensure_ascii=False))
        return
    if args.provider == "webhook":
        url = os.environ.get("DIGEST_WEBHOOK_URL")
        if not url:
            sys.exit("DIGEST_WEBHOOK_URL is required for --provider webhook")
        status, resp = post_json(url, {"subject": subject, "body": body})
        print(json.dumps({"provider": "webhook", "status": status, "body": resp}, ensure_ascii=False))
    elif args.provider == "buttondown":
        key = os.environ.get("BUTTONDOWN_API_KEY")
        if not key:
            sys.exit("BUTTONDOWN_API_KEY is required for --provider buttondown")
        status, resp = post_json(
            "https://api.buttondown.com/v1/emails",
            {"subject": subject, "body": body, "status": "about_to_send"},
            headers={"Authorization": "Token " + key},
        )
        print(json.dumps({"provider": "buttondown", "status": status, "body": resp}, ensure_ascii=False))
    elif args.provider == "resend":
        key = os.environ.get("RESEND_API_KEY")
        frm = os.environ.get("DIGEST_FROM")
        if not key or not frm or not args.to:
            sys.exit("RESEND_API_KEY, DIGEST_FROM and --to are required for --provider resend")
        status, resp = post_json(
            "https://api.resend.com/emails",
            {"from": frm, "to": [args.to], "subject": subject, "text": body},
            {"Authorization": f"Bearer {key}"},
        )
        print(json.dumps({"provider": "resend", "status": status, "body": resp}, ensure_ascii=False))


if __name__ == "__main__":
    main()
