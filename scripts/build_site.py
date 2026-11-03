#!/usr/bin/env python3
"""Build a zero-login, row-based product-internship site from jobs.json.

Each row: cover on the left, application-focused text on the right.
No original body / comment evidence / duplicate source link.
"""
import argparse, html, json, re, shutil
from datetime import datetime
from pathlib import Path


def esc(s):
    return html.escape(str(s or ""))


def cover(job, images_dir, asset_dir):
    pid = str(job.get("post_id", ""))
    if images_dir:
        src = Path(images_dir) / pid / "0.jpg"
        if src.exists():
            asset_dir.mkdir(parents=True, exist_ok=True)
            dst = asset_dir / f"{pid}.jpg"
            if not dst.exists():
                shutil.copy2(src, dst)
            return f"{asset_dir.name}/{pid}.jpg"
    imgs = job.get("images") or []
    return imgs[0] if imgs else ""


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def emails(value):
    text = flat(value)
    found = list(dict.fromkeys(EMAIL_RE.findall(text)))
    return "; ".join(found) if found else text


def flat(value):
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


def copy_text(job):
    parts = []
    if job.get("email"):
        parts.append(emails(job["email"]))
    if job.get("referral_code"):
        parts.append("内推码：" + str(job["referral_code"]))
    elif job.get("contact") and flat(job.get("contact")) not in ("-", "", "邮箱", "私信"):
        parts.append(flat(job.get("contact")))
    if not parts:
        parts.append(str(job.get("source_url") or ""))
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="data/jobs.json")
    ap.add_argument("out", nargs="?", default="docs/index.html")
    ap.add_argument("--images-dir", default="")
    ap.add_argument("--site-url", default="https://example.github.io/product-intern-daily/")
    args = ap.parse_args()

    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    active = [j for j in jobs if not j.get("closed")]
    closed = [j for j in jobs if j.get("closed")]
    today = datetime.now().astimezone().date().isoformat()
    new_today = [j for j in active if str(j.get("first_seen_at") or j.get("published_at") or "")[:10] == today]
    out_path = Path(args.out)
    out_dir = out_path.parent
    asset_dir = out_dir / "covers"
    rows = []
    for j in active:
        img = cover(j, args.images_dir, asset_dir)
        img_html = f"<img src='{esc(img)}' alt='cover' loading='lazy'>" if img else "<div class='placeholder'>产品实习</div>"
        pos = j.get("position") or ""
        if "未识别" in pos or not pos:
            pos = j.get("title") or pos
        email = emails(j.get("email"))
        ref = flat(j.get("referral_code"))
        contact = flat(j.get("contact"))
        source = str(j.get("source_url") or "").strip()
        if email:
            apply_value = email
            extra = f"<span class='ref'>内推码 {esc(ref)}</span>" if ref else ""
        elif ref:
            apply_value = f"内推码 {ref}"
            extra = ""
        elif contact and contact not in ("-",):
            apply_value = contact
            extra = ""
        else:
            apply_value = "见原帖"
            extra = ""
        payload = copy_text(j)
        rows.append(f"""<article class="row" data-status="{esc(j.get('still_hiring'))}">
  <div class="thumb">{img_html}</div>
  <div class="content">
    <div class="meta"><span class="badge {'open' if j.get('still_hiring')=='在招' else 'unknown'}">{esc(j.get('still_hiring'))}</span>
      <span>{esc(j.get('base_location') or j.get('location') or 'Base 待确认')}</span>
      <span>{esc(j.get('employment_type') or '类型待确认')}</span>
      {('<span>'+esc(j.get('salary'))+'</span>') if j.get('salary') else ''}
      <span class="convert">{'可转正' if j.get('convertible') else '日常实习'}</span></div>
    <div class="company">{esc(j.get('company') or '未识别')}</div>
    <h2>{esc(pos)}</h2>
    <div class="date">发布 {esc(str(j.get('published_at') or '')[:10])}</div>
    <div class="desc">{esc(j.get('description') or '（原帖未抓到正文，点“见原帖”查看）')}</div>
    <div class="apply">
      <span class="label">投递</span>
      <span class="value">{esc(apply_value)}</span>
      {extra}
      <button class="copy" data-copy="{esc(payload)}">复制</button>
      <a class="source" href="{esc(source)}" target="_blank" rel="noreferrer">投递：见原帖 ↗</a>
    </div>
  </div>
</article>""")
    closed_rows = "".join(
        f"<tr><td>{esc(j.get('company'))}</td><td>{esc(j.get('position'))}</td><td>{esc(str(j.get('published_at') or '')[:10])}</td><td>{esc(j.get('status_evidence') or j.get('excluded_reason'))}</td></tr>"
        for j in closed
    )
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>产品实习日报 · Product Intern Daily</title>
<style>
:root{{--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--bg:#f6f8fa;--accent:#0969da}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}
header{{background:#fff;border-bottom:1px solid var(--line)}} .wrap{{max-width:1100px;margin:0 auto;padding:0 24px}}
.hero{{padding:34px 0 16px}} h1{{margin:0 0 8px;font-size:30px}} .sub{{color:var(--muted);margin:0 0 14px}}
.stats{{display:flex;gap:18px;flex-wrap:wrap;color:var(--muted);font-size:14px}} .stats b{{color:var(--fg)}}
.toolbar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:12px 0 18px}}
input{{width:min(460px,100%);padding:10px 12px;border:1px solid var(--line);border-radius:10px;font-size:15px}}
.btn{{padding:9px 14px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--fg);text-decoration:none;font-size:14px}}
main{{max-width:1100px;margin:0 auto;padding:20px 24px 40px}}
.list{{display:flex;flex-direction:column;gap:12px}}
.row{{display:flex;background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden}}
.thumb{{flex:0 0 220px;width:220px;min-height:165px;background:#fff;display:flex;align-items:center;justify-content:center;border-right:1px solid var(--line)}}
.thumb img{{width:100%;height:100%;object-fit:cover;display:block}}
.placeholder{{color:var(--muted);font-weight:600;font-size:14px}}
.content{{padding:14px 18px;flex:1;min-width:0}}
.meta{{display:flex;gap:8px;flex-wrap:wrap;color:var(--muted);font-size:12px;align-items:center}}
.badge{{padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600}} .badge.open{{background:#dafbe1;color:#1a7f37}} .badge.unknown{{background:#fff8c5;color:#9a6700}}
.convert{{background:#ddf4ff;color:#0969da;padding:1px 7px;border-radius:999px;font-size:11px}}
.company{{color:var(--muted);font-size:13px;margin-top:6px}}
h2{{margin:0 0 10px;font-size:20px;line-height:1.35}}
.apply{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#f6f8fa;border-radius:10px;padding:8px 10px;font-size:14px}}
.apply .label{{color:var(--muted);font-size:12px;border:1px solid var(--line);padding:1px 6px;border-radius:6px}}
.apply .value{{font-weight:600;word-break:break-all}} .ref{{color:#9a6700;font-size:12px}}
.copy{{border:1px solid var(--line);background:#fff;border-radius:7px;padding:3px 9px;font-size:12px;cursor:pointer}}
.source{{margin-left:auto;color:var(--accent);font-size:13px;text-decoration:none;white-space:nowrap}}
.date{{color:var(--muted);font-size:12px;margin-top:8px}}
.desc{{white-space:pre-wrap;color:#3d444d;font-size:13px;line-height:1.55;margin-top:8px;max-height:12em;overflow:auto}}
.closed{{max-width:1100px;margin:10px auto;padding:0 24px}} table{{width:100%;border-collapse:collapse;background:#fff;font-size:14px}} th,td{{border:1px solid var(--line);padding:8px;text-align:left}}
footer{{max-width:1100px;margin:20px auto;padding:0 24px 30px;color:var(--muted);font-size:13px}}
@media(max-width:700px){{.row{{flex-direction:column}} .thumb{{flex:none;width:100%;height:180px;border-right:0;border-bottom:1px solid var(--line)}} .source{{margin-left:0}} h1{{font-size:24px}} main{{padding:14px}}}}
</style></head><body>
<header><div class="wrap"><div class="hero">
<h1>产品实习日报 · Product Intern Daily</h1>
<p class="sub">每天更新，只收产品实习。左边封面，右边投递方式；一键复制邮箱，点“见原帖”直接打开。</p>
<div class="stats"><span>在库 <b>{len(jobs)}</b></span><span>今日新增 <b>{len(new_today)}</b></span><span>在招/待确认 <b>{len(active)}</b></span><span>已截止 <b>{len(closed)}</b></span></div>
</div><div class="toolbar">
<input id="q" placeholder="搜索公司 / 岗位 / Base / 邮箱" oninput="filterRows()">
<a class="btn" href="feed.xml">RSS</a><a class="btn" href="subscribe.html">邮件订阅</a>
</div></div></header>
<main><div class="list" id="list">{''.join(rows)}</div></main>
<section class="closed"><h2>已截止 / 已招到</h2><table><thead><tr><th>公司</th><th>岗位</th><th>发布</th><th>依据</th></tr></thead><tbody>{closed_rows}</tbody></table></section>
<footer>数据来自公开帖子，仅供参考；投递前请核实身份。想删除自己的帖子/邮箱，请开 Issue。 · <a href="{esc(args.site_url)}">GitHub Pages</a></footer>
<script>
function filterRows(){{const q=document.getElementById('q').value.toLowerCase();for(const r of document.querySelectorAll('#list .row')){{r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';}}}}
document.querySelectorAll('.copy').forEach(btn=>btn.addEventListener('click',async()=>{{
  const text=btn.dataset.copy||'';
  try{{await navigator.clipboard.writeText(text);btn.textContent='已复制';setTimeout(()=>btn.textContent='复制',1500);}}
  catch(e){{const ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();btn.textContent='已复制';setTimeout(()=>btn.textContent='复制',1500);}}
}}));
</script></body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(doc, encoding="utf-8")
    print(json.dumps({"jobs": len(jobs), "active": len(active), "closed": len(closed), "new_today": len(new_today), "out": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
