#!/usr/bin/env python3
"""Render the full historical jobs pool as docs/HISTORY.md."""
import argparse, json, re
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
def cell(s): return str(s or '').replace('|','\\|').replace('\n',' ').strip()
def email_of(j):
    v=j.get('email'); t='; '.join(v) if isinstance(v,(list,tuple)) else str(v or '')
    f=list(dict.fromkeys(EMAIL_RE.findall(t))); return '; '.join(f) if f else ''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--jobs',default='data/jobs.json'); ap.add_argument('--out',default='docs/HISTORY.md'); a=ap.parse_args()
    jobs=json.loads(Path(a.jobs).read_text())['jobs']
    jobs.sort(key=lambda j:(str(j.get('first_seen_at') or j.get('published_at') or ''),str(j.get('company') or '')),reverse=True)
    lines=['# 历史岗位池','',f'累计 **{len(jobs)}** 条；GitHub 今日表格只展示 T-1 新增，这里是历史池（含已截止）。','', '| 首次收录 | 公司 | 岗位 | Base | 投递 | 状态 | 转正 |','|---|---|---|---|---|---|---|']
    for j in jobs:
        e=email_of(j); apply=f'[{e}](mailto:{e})' if e else '[见原帖]('+str(j.get('source_url') or '')+')'
        lines.append('| '+' | '.join([cell(str(j.get('first_seen_at') or j.get('published_at') or '')[:10]),cell(j.get('company') or '公司未注明'),f"[{cell(j.get('position') or j.get('title'))}]({j.get('source_url','')})",cell(j.get('base_location') or j.get('location') or '待确认'),apply,cell('已截止' if j.get('closed') else (j.get('still_hiring') or '无法确认')),'可转正' if j.get('convertible') else '日常实习'])+' |')
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text('\n'.join(lines)+'\n',encoding='utf-8'); print(a.out)

if __name__=='__main__': main()
