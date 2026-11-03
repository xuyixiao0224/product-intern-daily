"""Prepare agent extraction tasks and import the agent's JSON back into SQLite."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Job, STATUSES, now_iso
from .normalize import make_dedup_key, normalize_emails
from .store import Store

INSTRUCTIONS = """你是招聘信息抽取器。只输出 JSON，不要 Markdown。
对每个 task 输出一个对象，字段见 schema。
判断依据必须来自 description / comments / ocr_text，不能编造。
"""

SCHEMA = {
    "post_id": "string",
    "is_job_post": "boolean",
    "company": "string",
    "position": "string",
    "email": ["string"],
    "contact": "string",
    "location": "string",
    "employment_type": "string",
    "salary": "string",
    "still_hiring": "在招|已截止|已招到|无法确认",
    "status_evidence": "string，引用作者回复/正文二编/标题原话",
    "confidence": "0-1 number",
    "reason": "string",
}


def _iso(ms: int | float | None) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(float(ms) / 1000, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def flatten_comments(detail: dict) -> list[dict]:
    out: list[dict] = []
    comments = ((detail.get("data") or {}).get("comments") or {}).get("list") or []
    for c in comments:
        out.append(
            {
                "author": (c.get("userInfo") or {}).get("nickname", ""),
                "is_author": "is_author" in (c.get("showTags") or []),
                "content": c.get("content", "") or "",
                "created_at": _iso(c.get("createTime")),
                "like_count": c.get("likeCount", ""),
                "pinned": "user_top" in (c.get("showTags") or []),
                "pictures": c.get("pictures") or c.get("imageList") or c.get("images") or [],
                "has_image": bool(c.get("pictures") or c.get("imageList") or c.get("images")),
            }
        )
        for sc in c.get("subComments") or []:
            out.append(
                {
                    "author": (sc.get("userInfo") or {}).get("nickname", ""),
                    "is_author": "is_author" in (sc.get("showTags") or []),
                    "content": sc.get("content", "") or "",
                    "created_at": _iso(sc.get("createTime")),
                    "like_count": sc.get("likeCount", ""),
                    "pinned": False,
                    "pictures": sc.get("pictures") or sc.get("imageList") or sc.get("images") or [],
                    "has_image": bool(sc.get("pictures") or sc.get("imageList") or sc.get("images")),
                }
            )
    return out


def image_urls(detail: dict) -> list[str]:
    note = (detail.get("data") or {}).get("note") or {}
    urls = []
    for im in note.get("imageList") or []:
        url = im.get("urlDefault") or im.get("urlPre") or ""
        if url:
            urls.append(url)
    return urls


def source_url(post_id: str, token: str) -> str:
    return f"https://www.xiaohongshu.com/explore/{post_id}?xsec_token={token}&xsec_source=pc_search"


def content_hash(title: str, description: str, ocr: str, comments: list[dict]) -> str:
    h = hashlib.sha256()
    for part in (title, description, ocr, json.dumps(comments[-30:], ensure_ascii=False, sort_keys=True)):
        h.update((part or "").encode("utf-8"))
    return h.hexdigest()


def prepare_tasks(details_dir: str | Path, out_path: str | Path, limit: int | None = None) -> int:
    tasks = []
    for path in sorted(Path(details_dir).glob("*.json")):
        try:
            detail = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        note = (detail.get("data") or {}).get("note") or {}
        post_id = note.get("noteId") or path.stem
        comments = flatten_comments(detail)
        pinned = next((c["content"] for c in comments if c.get("pinned") and c.get("content")), "")
        tasks.append(
            {
                "post_id": post_id,
                "title": note.get("title", ""),
                "description": note.get("desc", ""),
                "author": (note.get("user") or {}).get("nickname", ""),
                "published_at": _iso(note.get("time")),
                "comments": comments,
                "pinned_comment": pinned,
                "ocr_text": detail.get("_ocr", ""),
                "images": image_urls(detail),
                "source_url": source_url(post_id, note.get("xsecToken", "")),
            }
        )
        if limit and len(tasks) >= limit:
            break
    payload = {"instructions": INSTRUCTIONS, "schema": SCHEMA, "tasks": tasks}
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(tasks)


def _load_extractions(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("extractions") or data.get("results") or []
    if not isinstance(data, list):
        raise ValueError("extractions must be a JSON list or {'extractions': [...]}")
    return data


def validate_extraction(item: dict) -> dict:
    if not item.get("post_id"):
        raise ValueError("missing post_id")
    if not isinstance(item.get("is_job_post"), bool):
        raise ValueError(f"{item['post_id']}: is_job_post must be boolean")
    status = item.get("still_hiring") or "无法确认"
    closed = bool(item.get("closed"))
    if status in ("已截止", "已招到"):
        status, closed = "无法确认", True
    if status not in STATUSES:
        raise ValueError(f"{item['post_id']}: invalid still_hiring={status!r}")
    confidence = item.get("confidence", 0)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.0
    referral = str(item.get("referral_code") or "").strip()
    if not referral:
        m = re.search(r"内推码[:：]?\s*([A-Za-z0-9_-]{4,})", str(item.get("description") or item.get("status_evidence") or ""))
        if m:
            referral = m.group(1)
    email = normalize_emails(item.get("email") or item.get("emails") or "")
    comment_email = normalize_emails(item.get("comment_email") or "")
    source = str(item.get("email_source") or "")
    if email and not source:
        source = "body"
    return {
        "post_id": str(item["post_id"]),
        "is_job_post": bool(item["is_job_post"]),
        "closed": closed,
        "convertible": bool(item.get("convertible")),
        "conversion_evidence": str(item.get("conversion_evidence") or ""),
        "company": str(item.get("company") or ""),
        "position": str(item.get("position") or ""),
        "email": email,
        "email_source": source,
        "comment_email": comment_email,
        "contact": str(item.get("contact") or ""),
        "referral_code": referral,
        "location": str(item.get("location") or ""),
        "base_location": str(item.get("base_location") or item.get("location") or ""),
        "employment_type": str(item.get("employment_type") or ""),
        "salary": str(item.get("salary") or ""),
        "still_hiring": status,
        "status_evidence": str(item.get("status_evidence") or ""),
        "confidence": confidence,
        "reason": str(item.get("reason") or ""),
        "excluded_reason": str(item.get("excluded_reason") or ""),
        "pinned_comment": str(item.get("pinned_comment") or ""),
        "comment_flags": str(item.get("comment_flags") or ""),
        "author_notes": int(item.get("author_notes") or 0),
        "author_companies": int(item.get("author_companies") or 0),
    }

def build_job(extraction: dict, detail: dict | None, *, ocr_text: str = "") -> Job:
    ex = validate_extraction(extraction)
    detail = detail or {}
    note = (detail.get("data") or {}).get("note") or {}
    post_id = ex["post_id"]
    token = note.get("xsecToken", "")
    comments = flatten_comments(detail)
    ocr = ocr_text or detail.get("_ocr", "") or ""
    published = _iso(note.get("time")) or ""
    job = Job(
        post_id=post_id,
        platform="xhs",
        source_url=source_url(post_id, token),
        author=(note.get("user") or {}).get("nickname", ""),
        published_at=published,
        title=note.get("title", ""),
        description=note.get("desc", ""),
        images=image_urls(detail),
        ocr_text=ocr,
        comments=comments,
        company=ex["company"],
        position=ex["position"],
        location=ex["location"],
        employment_type=ex["employment_type"],
        salary=ex["salary"],
        email=ex["email"],
        email_source=ex["email_source"],
        comment_email=ex["comment_email"],
        contact=ex["contact"],
        referral_code=ex["referral_code"],
        base_location=ex["base_location"],
        still_hiring=ex["still_hiring"],
        status_evidence=ex["status_evidence"],
        confidence=ex["confidence"],
        is_job_post=ex["is_job_post"],
        closed=ex["closed"],
        convertible=ex["convertible"],
        conversion_evidence=ex["conversion_evidence"],
        excluded_reason=ex["excluded_reason"],
        pinned_comment=ex["pinned_comment"],
        comment_flags=ex["comment_flags"],
        author_notes=ex["author_notes"],
        author_companies=ex["author_companies"],
        first_seen_at=now_iso(),
        last_seen_at=now_iso(),
        extracted_at=now_iso(),
        raw={"extraction": ex},
    )
    job.dedup_key = make_dedup_key(job.email, job.company, job.position, job.post_id)
    job.content_hash = content_hash(job.title, job.description, ocr, comments)
    return job


def import_extractions(path: str | Path, store: Store, details_dir: str | Path | None = None) -> dict:
    items = _load_extractions(path)
    details: dict[str, dict] = {}
    if details_dir:
        for p in Path(details_dir).glob("*.json"):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                pid = ((d.get("data") or {}).get("note") or {}).get("noteId") or p.stem
                details[pid] = d
            except Exception:
                continue
    ok = err = 0
    errors = []
    for item in items:
        try:
            job = build_job(item, details.get(str(item.get("post_id"))))
            store.upsert_job(job)
            ok += 1
        except Exception as exc:
            err += 1
            errors.append(f"{item.get('post_id', '?')}: {exc}")
    return {"imported": ok, "errors": err, "messages": errors}
