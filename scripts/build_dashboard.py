#!/usr/bin/env python3
"""Optional standalone export of the same README charts; no separate metrics."""
import argparse
import json
from pathlib import Path
from build_readme_charts import render_svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default="data/stats.json")
    ap.add_argument("--out", default="docs/dashboard.html")
    args = ap.parse_args()
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    panels = "".join(f'<section id="{mode}" {"" if mode == "day" else "hidden"}>{render_svg(stats, mode)}</section>' for mode in ("day", "week", "month"))
    doc = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>岗位收录趋势 · 产品实习日报</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f8fa;color:#1f2925;font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}main{max-width:948px;margin:48px auto;padding:0 24px}h1{font-size:26px;margin:0 0 8px}p{color:#66736c;margin:0 0 24px}nav{display:flex;gap:8px;margin-bottom:16px}button{padding:7px 20px;border:1px solid #d1d9e0;border-radius:20px;background:white;color:#66736c;cursor:pointer}button[aria-pressed=true]{background:#258564;color:white;border-color:#258564}svg{display:block;width:100%;height:auto}a{color:#258564}
</style><main><h1>岗位收录趋势</h1><p>最新新增是历史池的一部分；旧岗位更新不重复计数。</p><nav aria-label="统计粒度"><button data-mode="day" aria-pressed="true">按日</button><button data-mode="week" aria-pressed="false">按周</button><button data-mode="month" aria-pressed="false">按月</button></nav>'''
    doc += panels + '''<p>只展示本项目已记录的数据。当前周、月尚未结束；未记录日期不补零。</p></main><script>
document.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('section').forEach(s=>s.hidden=s.id!==button.dataset.mode)}));
</script></html>'''
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
