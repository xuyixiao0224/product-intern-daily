#!/usr/bin/env python3
"""Render the full historical jobs pool as Markdown and a paginated HTML page."""
import argparse, json, re
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def cell(s):
    return str(s or "").replace("|", "\\|").replace("\n", " ").strip()


def email_of(j):
    v = j.get("email")
    t = "; ".join(v) if isinstance(v, (list, tuple)) else str(v or "")
    found = list(dict.fromkeys(EMAIL_RE.findall(t)))
    return "; ".join(found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", default="data/jobs.json")
    ap.add_argument("--out", default="docs/HISTORY.md")
    ap.add_argument("--html", default="docs/history.html")
    a = ap.parse_args()
    jobs = json.loads(Path(a.jobs).read_text())["jobs"]
    jobs.sort(key=lambda j: (str(j.get("first_seen_at") or j.get("published_at") or ""), str(j.get("company") or "")), reverse=True)
    lines = [
        "# 历史岗位池",
        "",
        f"累计 **{len(jobs)}** 条；首页按「本期新增 / 往期岗位」分组；这里保留完整收录记录（含已截止），未标记截止不等于已确认在招。",
        "",
        "| 首次收录 | 公司 | 岗位 | Base | 投递 | 状态 | 转正 |",
        "|---|---|---|---|---|---|---|",
    ]
    for j in jobs:
        e = email_of(j)
        source = str(j.get("source_url") or "")
        apply = f"[{e}](mailto:{e})" if e else f"[见原帖]({source})"
        lines.append("| " + " | ".join([
            cell(str(j.get("first_seen_at") or j.get("published_at") or "")[:10]),
            cell(j.get("company") or "公司未注明"),
            f"[{cell(j.get('position') or j.get('title'))}]({source})",
            cell(j.get("base_location") or j.get("location") or "待确认"),
            apply,
            cell("已截止" if j.get("closed") else (j.get("still_hiring") or "无法确认")),
            "可转正" if j.get("convertible") else "日常实习",
        ]) + " |")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    rows = []
    for j in jobs:
        rows.append({
            "date": str(j.get("first_seen_at") or j.get("published_at") or "")[:10],
            "company": cell(j.get("company") or "公司未注明"),
            "position": cell(j.get("position") or j.get("title")),
            "base": cell(j.get("base_location") or j.get("location") or "待确认"),
            "email": email_of(j),
            "url": str(j.get("source_url") or ""),
            "status": "已截止" if j.get("closed") else (j.get("still_hiring") or "无法确认"),
            "convert": "可转正" if j.get("convertible") else "日常实习",
        })
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    template = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>历史岗位池 · 产品实习日报</title>
<style>
body{font:14px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;margin:0;background:#f6f8fa;color:#1f2328}
header{background:#fff;border-bottom:1px solid #d0d7de}.wrap{max-width:1200px;margin:0 auto;padding:0 20px}.hero{padding:28px 0 16px}h1{margin:0 0 6px}
table{width:100%;border-collapse:collapse;background:#fff}th,td{border-bottom:1px solid #d0d7de;padding:8px;text-align:left;vertical-align:top}th{background:#f6f8fa;position:sticky;top:0}a{color:#0969da}small{color:#656d76}
.bar{display:flex;gap:8px;align-items:center;margin:14px 0;flex-wrap:wrap}button,select,input{border:1px solid #d0d7de;border-radius:7px;background:#fff;padding:5px 9px}button:disabled{opacity:.4}.num{color:#656d76}
</style></head><body><header><div class="wrap hero"><h1>历史岗位池</h1><p class="num" id="sub"></p></div></header><main class="wrap">
<div class="bar"><button id="prev">上一页</button><span id="page" class="num"></span><button id="next">下一页</button><select id="size"><option>20</option><option>50</option><option>100</option></select><input id="q" placeholder="搜索公司/岗位/Base"></div>
<table><thead><tr><th>首次收录</th><th>公司</th><th>岗位</th><th>Base</th><th>投递</th><th>状态</th><th>转正</th></tr></thead><tbody id="rows"></tbody></table>
</main><script>
const DATA = __DATA__;
let page = 1, size = 20, q = "";
const $ = id => document.getElementById(id);
function filtered(){ return DATA.filter(x => !q || (x.company+x.position+x.base).toLowerCase().includes(q)); }
function render(){
  const f = filtered(), pages = Math.max(1, Math.ceil(f.length/size));
  page = Math.min(page, pages);
  $("sub").textContent = `共 ${DATA.length} 条，当前 ${f.length} 条`;
  $("page").textContent = `第 ${page} / ${pages} 页`;
  $("prev").disabled = page <= 1; $("next").disabled = page >= pages;
  $("rows").innerHTML = f.slice((page-1)*size, page*size).map(x => `<tr><td>${x.date}</td><td>${x.company}</td><td><a href="${x.url}" target="_blank">${x.position}</a></td><td>${x.base}</td><td>${x.email ? `<a href="mailto:${x.email}">${x.email}</a>` : `<a href="${x.url}" target="_blank">见原帖</a>`}</td><td>${x.status}</td><td>${x.convert}</td></tr>`).join("");
}
$("prev").onclick = () => { page--; render(); };
$("next").onclick = () => { page++; render(); };
$("size").onchange = e => { size = +e.target.value; page = 1; render(); };
$("q").oninput = e => { q = e.target.value.toLowerCase(); page = 1; render(); };
render();
</script></body></html>'''
    Path(a.html).write_text(template.replace("__DATA__", data), encoding="utf-8")
    print(a.out, a.html)


if __name__ == "__main__":
    main()
