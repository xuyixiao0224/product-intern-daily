"""CSV / HTML export with email-first deduplication."""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from .models import Job

CSV_COLUMNS = [
    "email", "company", "position", "published_at", "still_hiring", "status_evidence",
    "base", "location", "employment_type", "salary", "contact", "referral_code",
    "email_source", "comment_email", "pinned_comment", "source_url", "post_id",
    "confidence", "closed", "convertible", "conversion_evidence", "excluded_reason", "dedup_key",
]


def dedup_jobs(jobs: list[Job]) -> list[Job]:
    """Keep the best record per dedup_key.

    Priority: has email > newer published_at > higher confidence.
    """
    groups: dict[str, list[Job]] = {}
    for job in jobs:
        groups.setdefault(job.dedup_key or f"note:{job.post_id}", []).append(job)
    out = []
    for group in groups.values():
        group.sort(key=lambda j: (bool(j.email), j.published_at or "", j.confidence), reverse=True)
        out.append(group[0])
    out.sort(key=lambda j: (j.published_at or "", j.post_id), reverse=True)
    return out


def summary(jobs: list[Job]) -> dict:
    return {
        "total": len(jobs),
        "active": sum(1 for j in jobs if j.still_hiring == "在招"),
        "closed": sum(1 for j in jobs if j.still_hiring in ("已截止", "已招到")),
        "unknown": sum(1 for j in jobs if j.still_hiring == "无法确认"),
        "with_email": sum(1 for j in jobs if j.email),
        "emails": len({e for j in jobs for e in j.email.split(";") if e}),
        "latest": max((j.published_at for j in jobs), default=""),
    }


def export_csv(jobs: list[Job], path: str | Path) -> int:
    rows = dedup_jobs(jobs)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for j in rows:
            row = {k: getattr(j, k, "") for k in CSV_COLUMNS}
            row["base"] = j.base_location or j.location
            w.writerow(row)
    return len(rows)


def export_json(jobs: list[Job], path: str | Path) -> int:
    """Machine-readable feed (Swelist/SimplifyJobs style)."""
    rows = dedup_jobs(jobs)
    from datetime import datetime, timezone
    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "count": len(rows),
        "jobs": [j.to_dict() for j in rows],
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(rows)


def _cover(job: Job, images_dir: str | Path | None) -> str:
    if images_dir:
        p = Path(images_dir) / job.post_id / "0.jpg"
        if p.exists():
            return str(p)
    return job.images[0] if job.images else ""


def _comments_html(job: Job) -> str:
    lines = []
    for c in job.comments:
        if not c.get("content"):
            continue
        if c.get("is_author") or any(k in c["content"] for k in ("招", "投", "邮箱", "简历", "截止", "私信", "扫码", "base", "hc")):
            who = html.escape(c.get("author", ""))
            tag = "（作者）" if c.get("is_author") else ""
            lines.append(f"<li><code>{html.escape(c.get('created_at',''))}</code> <b>{who}</b>{tag}：{html.escape(c['content'])}</li>")
    return "<ul>" + "".join(lines[:8]) + "</ul>" if lines else "<p>无关键评论</p>"


def export_html(jobs: list[Job], path: str | Path, *, images_dir: str | Path | None = None, title: str = "小红书 AI 产品实习线索") -> int:
    rows = dedup_jobs(jobs)
    s = summary(rows)
    cards = []
    for j in rows:
        cover = _cover(j, images_dir)
        img = f'<img src="{html.escape(cover)}" alt="cover">' if cover else ""
        email = html.escape(j.email or "未公开")
        contact = html.escape(j.contact or "")
        evidence = html.escape(j.status_evidence or "")
        desc = html.escape(j.description or "")
        cards.append(
            f"""<section class="card">
  <h3>{html.escape(j.company or '未识别')}｜{html.escape(j.position or j.title)}</h3>
  {img}
  <p><b>邮箱：</b>{email}　<b>状态：</b><span class="status">{html.escape(j.still_hiring)}</span></p>
  <p><b>发布：</b>{html.escape(j.published_at[:10])}　<b>Base：</b>{html.escape(j.base_location or j.location or '待确认')}　<b>类型：</b>{html.escape(j.employment_type or '')}</p>
  <p><b>内推码：</b>{html.escape(j.referral_code or '—')}　<b>邮箱来源：</b>{html.escape(j.email_source or '—')}　<b>评论邮箱：</b>{html.escape(j.comment_email or '—')}</p>
  <p><b>转正：</b>{'可转正' if j.convertible else '日常实习'}</p>
  <p><b>证据：</b>{evidence}</p>
  <p><a href="{html.escape(j.source_url)}">打开原帖</a>　<b>置信度：</b>{j.confidence:.2f}</p>
  <details><summary>正文</summary><pre>{desc}</pre></details>
  <details><summary>评论关键证据</summary>{_comments_html(j)}</details>
</section>"""
        )
    html_doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{margin:0;background:#f6f8fa;color:#1f2328;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}
main{{max-width:1000px;margin:24px auto;padding:28px 36px;background:#fff;border:1px solid #d0d7de;border-radius:12px}}
h1{{border-bottom:1px solid #d0d7de;padding-bottom:10px}}
.card{{border:1px solid #d0d7de;border-radius:10px;padding:16px;margin:18px 0;background:#fbfcfd}}
.card img{{max-width:360px;width:100%;border-radius:8px;border:1px solid #d0d7de}}
.status{{color:#0969da;font-weight:600}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{border:1px solid #d0d7de;padding:8px}}th{{background:#f6f8fa}}
pre{{white-space:pre-wrap;background:#f6f8fa;padding:10px;border-radius:8px}}
details{{margin:8px 0}} summary{{cursor:pointer;color:#57606a}}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<p>共 {s['total']} 条去重后线索；在招 {s['active']}；有邮箱 {s['with_email']}；邮箱数 {s['emails']}；最新 {html.escape(s['latest'][:10])}</p>
{''.join(cards)}
</main></body></html>"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_doc, encoding="utf-8")
    return len(rows)
