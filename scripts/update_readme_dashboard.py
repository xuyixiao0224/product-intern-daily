#!/usr/bin/env python3
import argparse, json
from pathlib import Path
START='<!-- DASHBOARD:START -->'; END='<!-- DASHBOARD:END -->'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--stats',default='data/stats.json'); ap.add_argument('--readme',default='README.md'); a=ap.parse_args()
 s=json.loads(Path(a.stats).read_text()); rows=s.get('by_date') or []; today=rows[-1] if rows else {}
 block=f'''{START}
## 数据看板

| 指标 | 数值 |
|---|---:|
| 今日新增 | {today.get('new',0)} |
| 历史累计 | {s.get('total',0)} |
| 当前在招 | {s.get('active',0)} |
| 可转正 | {s.get('convertible',0)} |
| 有邮箱 | {s.get('with_email',0)} |

[打开交互看板（日/周/月） →](https://xuyixiao0224.github.io/product-intern-daily/dashboard.html)

**历史池 vs 今日新增**：GitHub 表格只列今日新增；`data/jobs.json` 是历史池，已截止会保留但不再出现在今日表；看板展示历史趋势。
{END}'''
 p=Path(a.readme); text=p.read_text()
 if START in text and END in text:
  import re; text=re.sub(re.escape(START)+r'.*?'+re.escape(END),block,text,flags=re.S)
 else:
  text=text.replace('<!-- JOBS:END -->','<!-- JOBS:END -->\n\n'+block,1)
 p.write_text(text); print(a.readme)
if __name__=='__main__': main()
