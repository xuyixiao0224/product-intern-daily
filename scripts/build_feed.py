#!/usr/bin/env python3
"""Build an RSS 2.0 feed from jobs.json."""
import json, sys
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape


def parse_dt(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return datetime.now().astimezone()


def main(src="data/jobs.json", out="docs/feed.xml", site="https://example.github.io/product-intern-daily/"):
    data = json.loads(Path(src).read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    jobs = [j for j in jobs if not j.get("closed")][:50]
    items = []
    for j in jobs:
        title = f"{j.get('company')}｜{j.get('position')}｜{j.get('base_location') or j.get('location') or ''}"
        desc = f"{j.get('still_hiring')} · {j.get('email') or '投递方式见原帖'} · {j.get('source_url')}"
        items.append(
            f"<item><title>{escape(title)}</title><link>{escape(j.get('source_url',''))}</link>"
            f"<guid isPermaLink=\"false\">{escape(j.get('post_id',''))}</guid>"
            f"<description>{escape(desc)}</description>"
            f"<pubDate>{format_datetime(parse_dt(j.get('published_at')))}</pubDate></item>"
        )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>产品实习日报 · Product Intern Daily</title>
<link>{escape(site)}</link>
<description>每日更新的产品实习线索（公司/岗位/Base/邮箱/状态）</description>
<language>zh-CN</language>
<lastBuildDate>{format_datetime(datetime.now().astimezone())}</lastBuildDate>
{''.join(items)}
</channel></rss>"""
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(xml, encoding="utf-8")
    print(json.dumps({"items": len(items), "out": out}, ensure_ascii=False))


if __name__ == "__main__":
    main(*(sys.argv[1:4] or []))
