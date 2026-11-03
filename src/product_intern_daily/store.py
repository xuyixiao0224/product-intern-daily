"""SQLite persistence: jobs, seen posts and run logs."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Job, now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    post_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL DEFAULT 'xhs',
    source_url TEXT,
    author TEXT,
    published_at TEXT,
    title TEXT,
    description TEXT,
    images_json TEXT,
    ocr_text TEXT,
    comments_json TEXT,
    company TEXT,
    position TEXT,
    location TEXT,
    employment_type TEXT,
    salary TEXT,
    email TEXT,
    email_source TEXT,
    comment_email TEXT,
    contact TEXT,
    referral_code TEXT,
    base_location TEXT,
    still_hiring TEXT,
    status_evidence TEXT,
    confidence REAL,
    is_job_post INTEGER NOT NULL DEFAULT 1,
    closed INTEGER NOT NULL DEFAULT 0,
    convertible INTEGER NOT NULL DEFAULT 0,
    conversion_evidence TEXT,
    excluded_reason TEXT,
    pinned_comment TEXT,
    comment_flags TEXT,
    author_notes INTEGER DEFAULT 0,
    author_companies INTEGER DEFAULT 0,
    dedup_key TEXT,
    content_hash TEXT,
    first_seen_at TEXT,
    last_seen_at TEXT,
    extracted_at TEXT,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_email ON jobs(email);
CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
CREATE INDEX IF NOT EXISTS idx_jobs_published ON jobs(published_at);
CREATE TABLE IF NOT EXISTS seen (
    post_id TEXT PRIMARY KEY,
    first_seen_at TEXT,
    last_fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    stats_json TEXT
);
"""


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._ensure_columns()
        self.conn.commit()

    def _ensure_columns(self) -> None:
        have = {r[1] for r in self.conn.execute("PRAGMA table_info(jobs)").fetchall()}
        cols = {
            "email_source": "TEXT", "comment_email": "TEXT", "referral_code": "TEXT",
            "base_location": "TEXT", "closed": "INTEGER NOT NULL DEFAULT 0",
            "excluded_reason": "TEXT", "pinned_comment": "TEXT", "comment_flags": "TEXT",
            "author_notes": "INTEGER DEFAULT 0", "author_companies": "INTEGER DEFAULT 0",
        }
        for name, typ in cols.items():
            if name not in have:
                self.conn.execute(f"ALTER TABLE jobs ADD COLUMN {name} {typ}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def upsert_job(self, job: Job) -> None:
        row = {
            "post_id": job.post_id,
            "platform": job.platform,
            "source_url": job.source_url,
            "author": job.author,
            "published_at": job.published_at,
            "title": job.title,
            "description": job.description,
            "images_json": json.dumps(job.images, ensure_ascii=False),
            "ocr_text": job.ocr_text,
            "comments_json": json.dumps(job.comments, ensure_ascii=False),
            "company": job.company,
            "position": job.position,
            "location": job.location,
            "employment_type": job.employment_type,
            "salary": job.salary,
            "email": job.email,
            "email_source": job.email_source,
            "comment_email": job.comment_email,
            "contact": job.contact,
            "referral_code": job.referral_code,
            "base_location": job.base_location,
            "still_hiring": job.still_hiring,
            "status_evidence": job.status_evidence,
            "confidence": float(job.confidence or 0),
            "is_job_post": 1 if job.is_job_post else 0,
            "closed": 1 if job.closed else 0,
            "convertible": 1 if job.convertible else 0,
            "conversion_evidence": job.conversion_evidence,
            "excluded_reason": job.excluded_reason,
            "pinned_comment": job.pinned_comment,
            "comment_flags": job.comment_flags,
            "author_notes": job.author_notes,
            "author_companies": job.author_companies,
            "dedup_key": job.dedup_key,
            "content_hash": job.content_hash,
            "first_seen_at": job.first_seen_at or now_iso(),
            "last_seen_at": job.last_seen_at or now_iso(),
            "extracted_at": job.extracted_at or now_iso(),
            "raw_json": json.dumps(job.raw, ensure_ascii=False),
        }
        cols = list(row)
        placeholders = ",".join("?" for _ in cols)
        updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "post_id")
        self.conn.execute(
            f"INSERT INTO jobs ({','.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(post_id) DO UPDATE SET {updates}, first_seen_at=COALESCE(jobs.first_seen_at, excluded.first_seen_at)",
            [row[c] for c in cols],
        )
        self.conn.commit()

    def get_job(self, post_id: str) -> Job | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE post_id=?", (post_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(
        self,
        *,
        since: str | None = None,
        status: str | None = None,
        include_rejected: bool = False,
        include_closed: bool = False,
    ) -> list[Job]:
        sql = "SELECT * FROM jobs WHERE 1=1"
        args: list = []
        if not include_rejected:
            sql += " AND is_job_post=1"
        if not include_closed:
            sql += " AND closed=0"
        if since:
            sql += " AND published_at >= ?"
            args.append(since)
        if status:
            sql += " AND still_hiring=?"
            args.append(status)
        sql += " ORDER BY published_at DESC, post_id DESC"
        return [self._row_to_job(r) for r in self.conn.execute(sql, args).fetchall()]

    def stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        jobs = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE is_job_post=1").fetchone()[0]
        active = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE is_job_post=1 AND still_hiring='在招'").fetchone()[0]
        with_email = self.conn.execute("SELECT COUNT(*) FROM jobs WHERE is_job_post=1 AND email<>''").fetchone()[0]
        latest = self.conn.execute("SELECT MAX(published_at) FROM jobs").fetchone()[0]
        return {"total": total, "job_posts": jobs, "active": active, "with_email": with_email, "latest": latest}

    def mark_seen(self, post_id: str, *, fetched: bool = False) -> None:
        now = now_iso()
        self.conn.execute(
            "INSERT INTO seen(post_id, first_seen_at, last_fetched_at) VALUES (?,?,?) "
            "ON CONFLICT(post_id) DO UPDATE SET last_fetched_at=COALESCE(excluded.last_fetched_at, seen.last_fetched_at)",
            (post_id, now, now if fetched else None),
        )
        self.conn.commit()

    def is_seen(self, post_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM seen WHERE post_id=?", (post_id,)).fetchone() is not None

    def record_run(self, command: str, started_at: str, stats: dict | None = None) -> None:
        self.conn.execute(
            "INSERT INTO runs(command, started_at, finished_at, stats_json) VALUES (?,?,?,?)",
            (command, started_at, now_iso(), json.dumps(stats or {}, ensure_ascii=False)),
        )
        self.conn.commit()

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            post_id=row["post_id"],
            platform=row["platform"] or "xhs",
            source_url=row["source_url"] or "",
            author=row["author"] or "",
            published_at=row["published_at"] or "",
            title=row["title"] or "",
            description=row["description"] or "",
            images=json.loads(row["images_json"] or "[]"),
            ocr_text=row["ocr_text"] or "",
            comments=json.loads(row["comments_json"] or "[]"),
            company=row["company"] or "",
            position=row["position"] or "",
            location=row["location"] or "",
            employment_type=row["employment_type"] or "",
            salary=row["salary"] or "",
            email=row["email"] or "",
            email_source=row["email_source"] or "",
            comment_email=row["comment_email"] or "",
            contact=row["contact"] or "",
            referral_code=row["referral_code"] or "",
            base_location=row["base_location"] or row["location"] or "",
            still_hiring=row["still_hiring"] or "无法确认",
            status_evidence=row["status_evidence"] or "",
            confidence=float(row["confidence"] or 0),
            is_job_post=bool(row["is_job_post"]),
            closed=bool(row["closed"]),
            convertible=bool(row["convertible"]),
            conversion_evidence=row["conversion_evidence"] or "",
            excluded_reason=row["excluded_reason"] or "",
            pinned_comment=row["pinned_comment"] or "",
            comment_flags=row["comment_flags"] or "",
            author_notes=int(row["author_notes"] or 0),
            author_companies=int(row["author_companies"] or 0),
            dedup_key=row["dedup_key"] or "",
            content_hash=row["content_hash"] or "",
            first_seen_at=row["first_seen_at"] or "",
            last_seen_at=row["last_seen_at"] or "",
            extracted_at=row["extracted_at"] or "",
            raw=json.loads(row["raw_json"] or "{}"),
        )


def upsert_many(store: Store, jobs: Iterable[Job]) -> int:
    n = 0
    for job in jobs:
        store.upsert_job(job)
        n += 1
    return n
