#!/usr/bin/env python3
"""Turn seed details + extractions into a filtered product-internship jobs.json."""
import argparse, json, re, subprocess, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.extract import flatten_comments

BJ = timezone(timedelta(hours=8))
HARD = ["全栈", "数据分析", "设计实习", "销售", "算法", "开发", "测试"]
PRODUCT = ["产品经理", "产品实习", "产品运营", "产品策划", "策略产品", "aipm", "产品助理", "产品岗", "产运"]


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def emails(value):
    text = flat(value)
    found = list(dict.fromkeys(EMAIL_RE.findall(text)))
    return "; ".join(found) if found else text


def flat(value):
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


def load_detail(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def image_list(detail):
    note = (detail.get("data") or {}).get("note") or {}
    return [im.get("urlDefault") or im.get("urlPre") for im in (note.get("imageList") or []) if im.get("urlDefault") or im.get("urlPre")]


def is_product(pos, desc, title=""):
    low_title = (title or "").lower()
    low_pos = (pos or "").lower()
    strong = ["产品经理", "产品实习", "产品运营", "产品策划", "产品设计", "产品体验设计", "策略产品", "ai产品", "产品助理", "产品岗", "产品实习生", "产运"]
    if any(k in low_pos for k in strong):
        return True
    # 标题必须出现“产品”，否则大概率是泛招聘/无关帖
    if "产品" not in low_title:
        return False
    if any(bad in (title or "") for bad in ("岗位表", "购买", "课程", "训练营", "付费")):
        return False
    if "未识别" in (pos or ""):
        return any(k in desc[:600].lower() for k in strong)
    return False

def cover(pid, urls, out_dir):
    if not urls:
        return ""
    dest_dir = out_dir / pid
    dest_dir.mkdir(parents=True, exist_ok=True)
    jpg = dest_dir / "0.jpg"
    if jpg.exists():
        return f"{pid}/0.jpg"
    raw = dest_dir / "0.raw"
    try:
        req = urllib.request.Request(urls[0], headers={"User-Agent": "Mozilla/5.0"})
        raw.write_bytes(urllib.request.urlopen(req, timeout=40).read())
        subprocess.run(["sips", "-s", "format", "jpeg", str(raw), "--out", str(jpg)], capture_output=True)
        raw.unlink(missing_ok=True)
        return f"{pid}/0.jpg" if jpg.exists() else ""
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--details", default="data/seed/details")
    ap.add_argument("--extractions", default="data/seed/extractions.json")
    ap.add_argument("--out", default="data/seed/jobs.json")
    ap.add_argument("--covers", default="data/seed/covers")
    ap.add_argument("--ai", default="", help="AI review JSON; overrides rule verdict/fields")
    args = ap.parse_args()
    details_dir = Path(args.details); covers_dir = Path(args.covers); covers_dir.mkdir(parents=True, exist_ok=True)
    exs = json.loads(Path(args.extractions).read_text(encoding="utf-8"))
    if isinstance(exs, dict):
        exs = exs.get("extractions", [])
    ai = {}
    if args.ai and Path(args.ai).exists():
        raw = json.loads(Path(args.ai).read_text(encoding="utf-8"))
        ai = {x.get("post_id"): x for x in raw if isinstance(x, dict)}
    jobs = []
    for ex in exs:
        if not ex.get("is_job_post") or ex.get("closed") or not ex.get("post_id"):
            continue
        a = ai.get(ex["post_id"]) or {}
        if a and (a.get("verdict") != "通过" or not a.get("is_product")):
            continue
        # AI 通过但没有任何投递方式：不进入日报（避免“只发岗位不留入口”）
        if a and not a.get("email") and not flat(ex.get("contact")) and not any(
            k in (ex.get("description") or "") for k in ("投递", "私信", "简历", "联系", "邮箱", "扫码")
        ):
            continue
        pos = str(a.get("position") or ex.get("position") or "")
        detail = load_detail(details_dir / f"{ex['post_id']}.json")
        note = (detail.get("data") or {}).get("note") or {}
        desc = note.get("desc") or ex.get("description") or ""
        if not a and not is_product(pos, desc, note.get("title", "")):
            continue
        urls = image_list(detail)
        ts = note.get("time")
        published = datetime.fromtimestamp(ts / 1000, BJ).isoformat(timespec="seconds") if ts else ex.get("published_at") or ""
        jobs.append({
            "post_id": ex["post_id"],
            "platform": "xhs",
            "source_url": ex.get("source_url") or "",
            "author": (note.get("user") or {}).get("nickname", ""),
            "published_at": published,
            "first_seen_at": published,
            "title": note.get("title", ""),
            "description": desc,
            "company": a.get("company") or ex.get("company", ""),
            "position": pos,
            "base_location": ex.get("base_location") or ex.get("location", ""),
            "location": ex.get("location", ""),
            "employment_type": ex.get("employment_type", ""),
            "salary": ex.get("salary", ""),
            "email": emails(a.get("email") or ex.get("email")),
            "email_source": "AI复核" if a.get("email") else ex.get("email_source", ""),
            "comment_email": flat(ex.get("comment_email")),
            "contact": flat(ex.get("contact")),
            "referral_code": flat(ex.get("referral_code")),
            "still_hiring": a.get("still_hiring") or ex.get("still_hiring", "无法确认"),
            "status_evidence": a.get("reason") or ex.get("status_evidence", ""),
            "closed": bool(ex.get("closed")),
            "convertible": bool(a.get("convertible")) if a else bool(ex.get("convertible")),
            "conversion_evidence": a.get("reason") if a else ex.get("conversion_evidence", ""),
            "excluded_reason": ex.get("excluded_reason", ""),
            "confidence": ex.get("confidence", 0),
            "dedup_key": "email:" + flat(ex.get("email")).split(";")[0].strip() if ex.get("email") else "note:" + ex["post_id"],
            "images": urls,
            "cover": cover(ex["post_id"], urls, covers_dir),
            "comments": flatten_comments(detail),
        })
    Path(args.out).write_text(json.dumps({"count": len(jobs), "jobs": jobs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "with_email": sum(1 for j in jobs if j.get("email")), "active": sum(1 for j in jobs if j.get("still_hiring") == "在招"), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
