#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.extract import flatten_comments
from product_intern_daily.normalize import extract_emails
from product_intern_daily.mcp_client import MCPClient

BASE = Path(__file__).resolve().parents[1]
D = BASE / "data/improve_details"
O = BASE / "data/improve_ocr"
IDS = {
    "6ae867320000000036028706": "购买表格/多公司引流",
    "6ae8257b000000000e026251": "内推码无邮箱",
    "6ae8710500000000350104a4": "第二张图邮箱",
    "6ae5e5b1000000002702f4c2": "第二张图邮箱+先不投",
    "6ae6e60a000000001802d294": "置顶评论图片（翻转）",
}
KNOWN = ["字节跳动", "腾讯", "阿里巴巴", "阿里", "百度", "美团", "快手", "小红书", "京东", "滴滴",
         "华为", "小米", "网易", "哔哩哔哩", "Shopee", "SHEIN", "科大讯飞", "月之暗面", "智谱",
         "MiniMax", "商汤", "拼多多", "携程", "得物", "蔚来", "理想", "小鹏", "海尔", "美的",
         "大疆", "OPPO", "vivo", "荣耀", "联想", "中储粮", "中信出版", "米哈游", "自然意志"]
DOMAIN = {"bytedance.com":"字节跳动","tencent.com":"腾讯","baidu.com":"百度","alibaba-inc.com":"阿里巴巴",
          "kuaishou.com":"快手","jd.com":"京东","apple.com":"Apple","iflytek.com":"科大讯飞",
          "xiaohongshu.com":"小红书","meituan.com":"美团","didiglobal.com":"滴滴"}
BUY = ["购买", "同款表格", "买同款", "付费", "课程", "训练营", "岗位表"]
HELP = re.compile(r"收到.{0,6}(终面|面试|offer)|请问.{0,10}(岗位|职业发展|前景)|有没有同岗|求建议|该不该|值不值得|怎么样", re.I)
CLOSE = ["先不投", "已招到", "已招满", "不收了", "不收啦", "停止招聘", "招满", "简历已筛完"]

def company_from_email(emails):
    for e in emails:
        d = e.split("@")[-1].lower()
        for k, v in DOMAIN.items():
            if d == k or d.endswith("." + k):
                return v
    return ""

def find_company(text):
    hits = []
    for name in KNOWN:
        if name in text:
            hits.append((len(name), name))
    return max(hits)[1] if hits else "未识别"

def find_base(text):
    m = re.search(r"(?:base|地点|坐标)[:：]?\s*(北京|上海|深圳|杭州|广州|成都|武汉|南京|苏州|西安|合肥|长沙|青岛|厦门|重庆|天津|无锡|佛山|东莞|珠海|香港|新加坡|美国|远程)", text, re.I)
    if m: return m.group(1)
    for c in ["北京","上海","深圳","杭州","广州","成都","武汉","南京","苏州","西安","合肥","长沙","青岛","厦门","重庆","天津","无锡","佛山","东莞","珠海","香港","新加坡","美国","远程"]:
        if c in text: return c
    return "待确认"

def clean_pos(title):
    t = re.sub(r"#.*$", "", title)
    t = re.sub(r"[【】\[\]]", "", t)
    t = re.sub(r"(急招|急聘|招人|招聘|内推|继任|有HC|有转正HC|可转正)", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip(" -—|·")[:60]

def author_check(detail):
    n = detail["data"]["note"]
    uid = (n.get("user") or {}).get("userId")
    tok = n.get("xsecToken")
    if not uid or not tok:
        return 0, [], "", False
    try:
        txt = MCPClient().call("user_profile", {"user_id": uid, "xsec_token": tok}, timeout=120)
        data = json.loads(txt)
    except Exception as e:
        return -1, [str(e)], "", False
    desc = ((data.get("userBasicInfo") or {}).get("desc") or "")
    comps = []
    for f in (data.get("feeds") or [])[:20]:
        c = find_company(((f.get("noteCard") or {}).get("displayTitle") or ""))
        if c != "未识别" and c not in comps:
            comps.append(c)
    aggr = any(k in desc for k in ("岗位表", "表格", "购买", "群", "每日更新", "校招", "内推"))
    return len(comps), comps, desc, aggr

rows = []
for pid, tag in IDS.items():
    d = json.loads((D / f"{pid}.json").read_text())
    n = d["data"]["note"]
    cs = flatten_comments(d)
    ct = "\n".join(c.get("content") or "" for c in cs)
    ot = (O / f"{pid}.txt").read_text() if (O / f"{pid}.txt").exists() else ""
    desc = n.get("desc") or ""
    body_em = extract_emails(desc)
    com_em = extract_emails(ct)
    ocr_em = extract_emails(ot)
    emails = list(dict.fromkeys(body_em + com_em + ocr_em))
    source = []
    if body_em: source.append("正文")
    if com_em: source.append("评论")
    if ocr_em: source.append("图片OCR")
    referral = ""
    m = re.search(r"内推码[:：]?\s*([A-Za-z0-9_-]{4,})", desc + "\n" + ct)
    if m: referral = m.group(1)
    pinned = next((c for c in cs if c.get("pinned")), None)
    pinned_text = (pinned or {}).get("content") or ""
    if not pinned_text:
        has_pic = bool((pinned or {}).get("has_image") or (pinned or {}).get("pictures"))
        pinned_text = "（置顶评论为图片，已 OCR）" if has_pic else "（置顶评论无文字；图片字段未返回）"
    buy = [k for k in BUY if k in ct]
    help_seek = bool(HELP.search(desc + " " + ct))
    closed = [k for k in CLOSE if k in desc or k in ct]
    active = []
    for c in cs:
        if c.get("is_author") and c.get("content"):
            if any(k in c["content"] for k in ("还在", "没删", "在招", "可以投", "有")):
                active.append(c["content"][:40])
    status = "无法确认"
    if closed:
        status = "无法确认"
    elif active:
        status = "在招"
    company = company_from_email(emails) or find_company(desc + " " + n.get("title", "") + " " + ot)
    base = find_base(desc + " " + ct)
    ncomp, comps, author_desc, aggr = (0, [], "", False)
    if not emails:
        ncomp, comps, author_desc, aggr = author_check(d)
    is_job = True
    reason = ""
    if buy:
        is_job = False; reason = "评论区出现购买/同款表格：" + ",".join(buy)
    elif help_seek:
        is_job = False; reason = "求助/职业咨询帖"
    elif ncomp > 2 and aggr and not emails:
        is_job = False; reason = f"作者主页/笔记出现 {ncomp} 家公司且简介含岗位表/购买等，疑似引流：{','.join(comps[:6])}"
    elif closed:
        reason = "作者/正文明确已截止：" + ",".join(closed)
    if not is_job:
        status = "无法确认"
    rows.append({
        "post_id": pid, "tag": tag, "title": n.get("title"), "company": company,
        "position": clean_pos(n.get("title", "")), "base": base,
        "emails": emails, "email_source": "/".join(source),
        "body_emails": body_em, "comment_emails": com_em, "ocr_emails": ocr_em,
        "referral_code": referral, "pinned_comment": pinned_text,
        "status": status, "closed": bool(closed), "status_evidence": ",".join(closed) or ";".join(active),
        "buy_flags": buy, "help_seeking": help_seek,
        "author_companies": ncomp, "author_company_list": comps, "author_desc": author_desc, "author_aggr": aggr,
        "is_job_post": is_job, "excluded_reason": reason,
    })

(BASE / "data/improve_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
import csv
with (BASE / "data/improve_results.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["标签","岗位","公司","Base","邮箱","邮箱来源","内推码","置顶评论","状态","已截止","是否招聘帖","排除原因","购买词","求助帖","作者公司数"])
    for r in rows:
        w.writerow([r["tag"], r["position"], r["company"], r["base"], ";".join(r["emails"]), r["email_source"], r["referral_code"], r["pinned_comment"][:80], r["status"], r["closed"], r["is_job_post"], r["excluded_reason"], ",".join(r["buy_flags"]), r["help_seeking"], r["author_companies"]])
for r in rows:
    print("="*100)
    print(r["tag"], "|", r["title"])
    print(" company:", r["company"], "| base:", r["base"], "| status:", r["status"], "| closed:", r["closed"])
    print(" emails:", r["emails"], "| source:", r["email_source"], "| referral:", r["referral_code"])
    print(" pinned:", r["pinned_comment"][:120])
    print(" buy:", r["buy_flags"], "| help:", r["help_seeking"], "| author_companies:", r["author_companies"], r["author_company_list"])
    print(" is_job:", r["is_job_post"], "| reason:", r["excluded_reason"])
