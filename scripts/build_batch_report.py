#!/usr/bin/env python3
import json, sys, os, re
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.store import Store
from product_intern_daily.extract import import_extractions
from product_intern_daily.export import export_csv, export_html, export_json, dedup_jobs, summary

BASE = Path(__file__).resolve().parents[1]
extractions = BASE / "data/extractions100.json"
details = BASE / "data/details100"
db = BASE / "data/run100.sqlite3"
out = BASE / "data/exports100"
out.mkdir(parents=True, exist_ok=True)

if db.exists():
    db.unlink()
with Store(db) as store:
    res = import_extractions(extractions, store, details)
    jobs = store.list_jobs()
    all_rows = store.list_jobs(include_rejected=True)
    stats = store.stats()

rows = dedup_jobs(jobs)
export_csv(rows, out / "jobs100.csv")
export_html(rows, out / "jobs100.html", images_dir=BASE / "data/images100")
s = summary(rows)

AI_KW = ["ai产品", "ai 产品", "产品经理", "产品实习", "产品策划", "策略产品",
         "aipm", "产品助理", "产品岗", "产品运营", "产运", "产品"]
HARD = ["全栈", "数据分析", "设计", "销售", "算法", "开发", "测试"]
CLEAR_PRODUCT = ["ai产品", "产品经理", "产品实习", "产品策划", "策略产品", "aipm", "产品运营"]
def is_ai_product(r):
    if r.get("closed") or r.get("still_hiring") in ("已截止", "已招到"):
        return False
    pos = (r.get("position") or "")
    desc = (r.get("description") or "")[:400].lower()
    text = (pos + " " + desc).lower()
    if any(k in pos for k in HARD):
        return False
    if not re.search(r"(?<![a-z])ai(?![a-z])|aigc|大模型|agent|llm|人工智能|智能体|openai|kimi|claude|gpt", text):
        return False
    if any(k in pos for k in ["产品", "产运"]):
        return True
    if pos != "未识别（见正文）":
        return False
    return any(k in desc for k in CLEAR_PRODUCT)

all_extractions = json.loads(extractions.read_text(encoding="utf-8"))
job_posts = [r for r in all_extractions if r.get("is_job_post")]
leads = [r for r in job_posts if is_ai_product(r)]
lead_ids = {r["post_id"] for r in leads}
lead_jobs = [j for j in rows if j.post_id in lead_ids]
lead_ids_final = {j.post_id for j in lead_jobs}
table_leads = [r for r in leads if r["post_id"] in lead_ids_final]
export_csv(lead_jobs, out / "leads100.csv")
export_html(lead_jobs, out / "leads100.html", images_dir=BASE / "data/images100")
export_json(lead_jobs, out / "leads100.json")


all_extractions = json.loads(extractions.read_text(encoding="utf-8"))
job_posts = [r for r in all_extractions if r.get("is_job_post")]
non_jobs = [r for r in all_extractions if not r.get("is_job_post")]
with_email = [r for r in job_posts if r.get("email")]
active = [r for r in job_posts if r.get("still_hiring") == "在招"]
closed = [r for r in job_posts if r.get("closed") or r.get("still_hiring") in ("已截止", "已招到")]
unknown = [r for r in job_posts if r.get("still_hiring") == "无法确认"]
companies = Counter(r.get("company") or "未识别" for r in job_posts)
types = Counter(r.get("employment_type") or "未知" for r in job_posts)
low = [r for r in job_posts if float(r.get("confidence") or 0) < 0.6]

lines = []
A = lines.append
A("# 100 条小红书岗位批量跑结果")
A("")
A(f"- 抓取详情：**{len(all_extractions)}** 条")
A(f"- 判定为招聘帖：**{len(job_posts)}** 条；其中 AI 产品相关：**{len(leads)}** 条（按邮箱/同岗位去重后 **{len(lead_jobs)}** 个岗位）")
A(f"- 非招聘/经验/个人求职：**{len(non_jobs)}** 条")
A(f"- 有邮箱（全部招聘帖）：**{len(with_email)}** 条（去重后 **{s['emails']}** 个）；AI 产品线索中：**{sum(1 for r in leads if r.get('email'))}** 条")
A(f"- 在招：**{len(active)}** 条；已截止（closed）：**{len(closed)}** 条；无法确认：**{len(unknown)}** 条")
A(f"- 低置信度（<0.6）：**{len(low)}** 条，建议人工复核")
A(f"- 导出：`{out / 'jobs100.csv'}` / `{out / 'jobs100.html'}` / `{out / 'leads100.csv'}`")
A("")
A("## 公司分布")
A("")
for k, v in companies.most_common(15):
    A(f"- {k}：{v}")
A("")
A("## 岗位类型")
A("")
for k, v in types.most_common():
    A(f"- {k}：{v}")
A("")
A("## 招聘帖表（按邮箱/在招/置信度排序）")
A("")
A("| 邮箱 | 公司 | 岗位 | Base | 发布 | 状态 | 内推码 | 置信度 |")
A("|---|---|---|---|---|---|---|---|")
def fmt_date(v):
    from datetime import datetime, timezone, timedelta
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    return str(v or "")[:10]

def key(r):
    return (bool(r.get("email")), r.get("still_hiring") == "在招", float(r.get("confidence") or 0), r.get("published_at") or "")
for r in sorted(table_leads, key=key, reverse=True):
    em = ";".join(r.get("email") or []) or "—"
    A(f"| {em} | {r.get('company','')} | {r.get('position','')} | {r.get('base_location') or r.get('location','')} | {fmt_date(r.get('published_at'))} | {r.get('still_hiring','')} | {r.get('referral_code','') or '—'} | {r.get('confidence',0)} |")
A("")
A("> 这是规则初筛 + 人工复核的结构化结果；低置信度/公司“未识别”行已标记，投递前仍需核实。")
(BASE / "data/batch100.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"imported": res, "stats": stats, "job_posts": len(job_posts), "ai_product_leads": len(leads), "with_email": len(with_email), "active": len(active), "closed": len(closed), "unknown": len(unknown), "low": len(low)}, ensure_ascii=False, indent=1))
