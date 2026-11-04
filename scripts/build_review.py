#!/usr/bin/env python3
"""Build a human-review HTML/CSV of every fetched note (no filtering)."""
import argparse, csv, html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

STRONG = ["产品经理", "产品实习", "产品运营", "产品策划", "策略产品", "ai产品", "产品助理", "产品岗", "产品实习生", "产运"]


def esc(s):
    return html.escape(str(s or ""))


def flat(v):
    return "; ".join(str(x).strip() for x in v if str(x).strip()) if isinstance(v, (list, tuple)) else str(v or "").strip()


def is_product(pos, desc, title):
    low_pos, low_title = (pos or "").lower(), (title or "").lower()
    if any(k in low_pos for k in STRONG):
        return True
    if "产品" not in low_title:
        return False
    if "未识别" in pos:
        return any(k in desc[:600].lower() for k in STRONG)
    return False


def status(ex, title, desc, ocr_ok):
    if not ex.get("is_job_post"):
        return "不通过", "非招聘帖"
    if ex.get("closed"):
        return "不通过", "已截止/先不投"
    if ex.get("buy_flags"):
        return "不通过", "购买表格/引流"
    if ex.get("help_seeking"):
        return "不通过", "求助/面经"
    pos = ex.get("position") or title
    if not is_product(pos, desc, title):
        return "不通过", "非产品岗"
    if not ocr_ok:
        return "待定", "OCR 失败，可能漏邮箱"
    return "通过", "产品岗" + ("（有邮箱）" if ex.get("email") else "（无邮箱）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--details", default="data/daily/2026-11-04/details")
    ap.add_argument("--extractions", default="data/daily/2026-11-04/extractions.json")
    ap.add_argument("--ocr", default="data/daily/2026-11-04/ocr")
    ap.add_argument("--out", default="data/review/2026-11-04.html")
    args = ap.parse_args()
    details = Path(args.details); ocr = Path(args.ocr)
    exs = json.loads(Path(args.extractions).read_text(encoding="utf-8"))
    rows = []
    for ex in exs:
        pid = ex["post_id"]
        d = json.loads((details / f"{pid}.json").read_text(encoding="utf-8"))
        note = (d.get("data") or {}).get("note") or {}
        title = note.get("title") or ""
        desc = note.get("desc") or ex.get("description") or ""
        ocr_path = ocr / f"{pid}.txt"
        ocr_ok = ocr_path.exists() and ocr_path.stat().st_size > 0
        verdict, reason = status(ex, title, desc, ocr_ok)
        rows.append({
            "id": pid, "title": title,
            "company": ex.get("company") or "", "position": ex.get("position") or "",
            "base": ex.get("base_location") or ex.get("location") or "",
            "email": flat(ex.get("email")), "hiring": ex.get("still_hiring") or "",
            "convertible": "可转正" if ex.get("convertible") else "日常",
            "ocr": "OK" if ocr_ok else "FAIL",
            "verdict": verdict, "reason": reason,
            "url": ex.get("source_url") or note.get("noteUrl") or "",
            "desc": desc[:240].replace("\n", " "),
        })
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    with (out.with_suffix(".csv")).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    trs = "\n".join(
        f"<tr class='{esc(r['verdict'])}'><td>{i}</td><td><b>{esc(r['company'] or '公司未注明')}</b><br>{esc(r['position'] or r['title'])}</td>"
        f"<td>{esc(r['base'])}<br><small>{esc(r['hiring'])} · {esc(r['convertible'])}</small></td>"
        f"<td>{esc(r['email'] or '—')}</td><td>{esc(r['ocr'])}</td><td><b>{esc(r['verdict'])}</b><br><small>{esc(r['reason'])}</small></td>"
        f"<td><a href='{esc(r['url'])}' target='_blank'>原帖</a><br><small>{esc(r['desc'])}</small></td></tr>"
        for i, r in enumerate(rows, 1)
    )
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>53 条人工复核 · 产品实习日报</title>
<style>body{{font:14px/1.5 -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;margin:24px;color:#1f2328}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d0d7de;padding:8px;vertical-align:top}}th{{background:#f6f8fa;position:sticky;top:0}}tr.通过{{background:#dafbe1}}tr.不通过{{background:#fff1f0}}tr.待定{{background:#fff8c5}}small{{color:#656d76}}a{{color:#0969da}}</style></head><body>
<h1>53 条人工复核</h1><p>抓取：2026-11-04 · 全量未筛选 · 通过/不通过只是规则建议，请人工最终判断。</p>
<table><thead><tr><th>#</th><th>公司 / 岗位</th><th>Base / 状态 / 转正</th><th>邮箱</th><th>OCR</th><th>规则结论</th><th>原帖 / 正文</th></tr></thead><tbody>{trs}</tbody></table></body></html>"""
    out.write_text(doc, encoding="utf-8")
    print(json.dumps({"rows": len(rows), "html": str(out), "csv": str(out.with_suffix(".csv"))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
