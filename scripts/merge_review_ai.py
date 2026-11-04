#!/usr/bin/env python3
import csv, html, json
from pathlib import Path

BASE = Path('data/review')
rows = list(csv.DictReader((BASE/'2026-11-04.csv').open(encoding='utf-8-sig')))
ai = {x['post_id']: x for x in json.load((BASE/'ai_2026-11-04.json').open())}

def e(s): return html.escape(str(s or ''))
out=[]
for i,r in enumerate(rows,1):
    a=ai.get(r['id'],{})
    r.update({
        'ai_verdict': a.get('verdict',''),
        'ai_company': a.get('company') or '',
        'ai_position': a.get('position') or '',
        'ai_email': a.get('email') or '',
        'ai_hiring': a.get('still_hiring') or '',
        'ai_reason': a.get('reason') or '',
        'ai_confidence': a.get('confidence',''),
    })
    out.append(r)
with (BASE/'2026-11-04-ai.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
trs='\n'.join(
    f"<tr class='{e(r['ai_verdict'])}'><td>{i}</td><td><b>{e(r['ai_company'] or r['company'] or '公司未注明')}</b><br>{e(r['ai_position'] or r['position'] or r['title'])}</td>"
    f"<td>{e(r['base'])}<br><small>{e(r['ai_hiring'])} · {e(r['convertible'])}</small></td>"
    f"<td>{e(r['ai_email'] or r['email'] or '—')}</td><td>{e(r['ocr'])}</td>"
    f"<td><b>规则：{e(r['verdict'])}</b><br><small>{e(r['reason'])}</small><hr><b>AI：{e(r['ai_verdict'])}</b><br><small>{e(r['ai_reason'])}</small></td>"
    f"<td><a href='{e(r['url'])}' target='_blank'>原帖</a><br><small>{e(r['desc'])}</small></td></tr>"
    for i,r in enumerate(out,1)
)
doc=f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>53 条规则+AI复核</title>
<style>body{{font:14px/1.5 -apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;margin:24px;color:#1f2328}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d0d7de;padding:8px;vertical-align:top}}th{{background:#f6f8fa;position:sticky;top:0}}tr.通过{{background:#dafbe1}}tr.不通过{{background:#fff1f0}}small{{color:#656d76}}hr{{border:0;border-top:1px solid #d0d7de;margin:6px 0}}a{{color:#0969da}}</style></head><body>
<h1>53 条：规则 + AI 复核</h1><p>AI：DeepSeek；规则与 AI 并列，最终由你判断。通过 {sum(1 for r in out if r['ai_verdict']=='通过')} / 不通过 {sum(1 for r in out if r['ai_verdict']=='不通过')}。</p>
<table><thead><tr><th>#</th><th>AI 公司 / 岗位</th><th>Base / 状态 / 转正</th><th>邮箱</th><th>OCR</th><th>规则 vs AI</th><th>原帖 / 正文</th></tr></thead><tbody>{trs}</tbody></table></body></html>"""
Path(BASE/'2026-11-04-ai.html').write_text(doc,encoding='utf-8')
print(JSON:=(BASE/'2026-11-04-ai.html').as_posix())
