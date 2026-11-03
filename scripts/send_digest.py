#!/usr/bin/env python3
"""Render (and optionally send) the daily product-internship digest.

Never uses a personal mailbox. Pick a transactional provider or a webhook:

  # preview only
  python scripts/send_digest.py --jobs data/jobs.json --dry-run

  # Buttondown/Listmonk/Zapier via webhook
  DIGEST_WEBHOOK_URL=https://... python scripts/send_digest.py --provider webhook

  # Resend test send (domain must be verified)
  RESEND_API_KEY=... DIGEST_FROM=digest@yourdomain.com \
    python scripts/send_digest.py --provider resend --to you@example.com
"""
import argparse, html, json, os, re, sys, urllib.request

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def emails(value):
    text = " ; ".join(value) if isinstance(value, (list, tuple)) else str(value or "")
    found = list(dict.fromkeys(EMAIL_RE.findall(text)))
    return "; ".join(found) if found else text
from datetime import datetime, timedelta
from pathlib import Path


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
    rows = []
    for j in jobs:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(j.get('company','')))}</td>"
            f"<td>{html.escape(str(j.get('position','')))}</td>"
            f"<td>{html.escape(str(j.get('base_location') or j.get('location') or ''))}</td>"
            f"<td>{html.escape(emails(j.get('email')) or '见原帖')}</td>"
            f"<td>{html.escape(str(j.get('still_hiring','')))}</td>"
            f"<td><a href=\"{html.escape(str(j.get('source_url','')))}\">原帖</a></td>"
            "</tr>"
        )
    doc = f"""<!doctype html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif">
<h2>产品实习日报 · {today}</h2>
<p>今日精选 {len(jobs)} 条。投递前请核实身份；回复邮件可退订。</p>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;font-size:14px">
<thead><tr><th>公司</th><th>岗位</th><th>Base</th><th>邮箱</th><th>状态</th><th>原帖</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p style="color:#666;font-size:12px">数据来自公开帖子，仅供参考；如需删除请联系维护者。</p>
</body></html>"""
    text = f"产品实习日报 {today}\n" + "\n".join(
        f"- {j.get('company')} | {j.get('position')} | {j.get('base_location') or j.get('location')} | {emails(j.get('email')) or '见原帖'} | {j.get('source_url')}"
        for j in jobs
    )
    return doc, text


def post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read().decode()[:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--since", default="1d", help="1d/7d or ISO date")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--provider", choices=["resend", "webhook"], default="")
    ap.add_argument("--to", default="", help="test recipient for Resend")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    jobs = select(load_jobs(args.jobs), args.since, args.limit)
    doc, text = render(jobs)
    out = Path("exports"); out.mkdir(exist_ok=True)
    (out / "digest.html").write_text(doc, encoding="utf-8")
    (out / "digest.txt").write_text(text, encoding="utf-8")
    if args.dry_run or not args.provider:
        print(json.dumps({"jobs": len(jobs), "dry_run": True, "html": "exports/digest.html"}, ensure_ascii=False))
        return
    subject = f"产品实习日报 · {datetime.now().astimezone():%Y-%m-%d}"
    if args.provider == "webhook":
        url = os.environ.get("DIGEST_WEBHOOK_URL")
        if not url:
            sys.exit("DIGEST_WEBHOOK_URL is required for --provider webhook")
        status, body = post_json(url, {"subject": subject, "html": doc, "text": text})
        print(json.dumps({"provider": "webhook", "status": status, "body": body}, ensure_ascii=False))
    elif args.provider == "resend":
        key = os.environ.get("RESEND_API_KEY")
        frm = os.environ.get("DIGEST_FROM")
        if not key or not frm or not args.to:
            sys.exit("RESEND_API_KEY, DIGEST_FROM and --to are required for --provider resend")
        status, body = post_json(
            "https://api.resend.com/emails",
            {"from": frm, "to": [args.to], "subject": subject, "html": doc, "text": text},
            {"Authorization": f"Bearer {key}"},
        )
        print(json.dumps({"provider": "resend", "status": status, "body": body}, ensure_ascii=False))


if __name__ == "__main__":
    main()
