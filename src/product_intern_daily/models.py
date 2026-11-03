"""Dataclasses shared by the CLI, store and exporter."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

STATUSES = ("在招", "无法确认")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def to_int(value: Any) -> int:
    try:
        return int(str(value).replace(",", "").strip() or 0)
    except (TypeError, ValueError):
        return 0


@dataclass
class Candidate:
    post_id: str
    token: str
    title: str = ""
    author: str = ""
    likes: int = 0
    comments: int = 0
    keyword: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Job:
    post_id: str
    platform: str = "xhs"
    source_url: str = ""
    author: str = ""
    published_at: str = ""
    title: str = ""
    description: str = ""
    images: list[str] = field(default_factory=list)
    ocr_text: str = ""
    comments: list[dict] = field(default_factory=list)
    company: str = ""
    position: str = ""
    location: str = ""
    employment_type: str = ""
    salary: str = ""
    email: str = ""
    email_source: str = ""
    comment_email: str = ""
    contact: str = ""
    referral_code: str = ""
    base_location: str = ""
    still_hiring: str = "无法确认"
    status_evidence: str = ""
    confidence: float = 0.0
    is_job_post: bool = True
    closed: bool = False
    convertible: bool = False
    conversion_evidence: str = ""
    excluded_reason: str = ""
    pinned_comment: str = ""
    comment_flags: str = ""
    author_notes: int = 0
    author_companies: int = 0
    dedup_key: str = ""
    content_hash: str = ""
    first_seen_at: str = ""
    last_seen_at: str = ""
    extracted_at: str = ""
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d
