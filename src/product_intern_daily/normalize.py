"""Email/company/position normalization and dedup keys."""
from __future__ import annotations

import re
import unicodedata

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_EMAIL_JUNK = re.compile(r"^(?:mailto:|email[:：]?)", re.I)
_PUNCT = re.compile(r"[\s\-—–_/|·,，。;；:：()（）\[\]【】\"'“”‘’]+")


def repair_ocr_emails(text: str) -> str:
    """Repair common OCR mistakes before email extraction.

    Examples: ``foo.gmail.com`` -> ``foo@gmail.com``; ``foo(at)bar.com``.
    """
    if not text:
        return ""
    text = text.replace("＠", "@")
    text = re.sub(r"\s*[\(\[（【]\s*at\s*[\)\]）】]\s*", "@", text, flags=re.I)
    text = re.sub(r"\s+at\s+", "@", text, flags=re.I)
    # OCR often drops @ and leaves a dot before a known mail domain.
    text = re.sub(
        r"([A-Za-z0-9._%+\-]+)\.(gmail|qq|163|126|outlook|foxmail|yahoo|hotmail|icloud)\.com",
        r"\1@\2.com",
        text,
        flags=re.I,
    )
    return text


def extract_emails(text: str | None) -> list[str]:
    """Extract unique, lowercased, de-duplicated emails from free text."""
    if not text:
        return []
    text = repair_ocr_emails(text)
    found = []
    for raw in EMAIL_RE.findall(text):
        e = raw.strip().strip(".").lower()
        e = _EMAIL_JUNK.sub("", e)
        # drop obvious image/file false positives
        if re.search(r"\.(?:png|jpe?g|webp|gif|svg|pdf)$", e):
            continue
        if e not in found:
            found.append(e)
    return found


def normalize_emails(value: str | list[str] | None) -> str:
    """Return a canonical semicolon-separated email string."""
    if value is None:
        return ""
    if isinstance(value, str):
        items = extract_emails(value) or ([value.strip().lower()] if "@" in value else [])
    else:
        items = []
        for v in value:
            items.extend(extract_emails(str(v)) or ([str(v).strip().lower()] if "@" in str(v) else []))
    out = []
    for e in items:
        e = e.strip().lower()
        if "@" in e and e not in out:
            out.append(e)
    return ";".join(out)


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value)
    value = _PUNCT.sub("", value)
    return value.strip().lower()


def make_dedup_key(email: str | None, company: str | None, position: str | None, post_id: str) -> str:
    """Email first, then company+position, then post id."""
    first = (email or "").split(";")[0].strip().lower()
    if first:
        return f"email:{first}"
    c, p = normalize_text(company), normalize_text(position)
    if c and p:
        return f"role:{c}|{p}"
    return f"note:{post_id}"


def slug(text: str) -> str:
    return normalize_text(text).replace(" ", "-") or "unknown"
