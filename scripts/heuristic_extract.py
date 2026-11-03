#!/usr/bin/env python3
"""Heuristic first-pass extraction for a batch of details.

This is intentionally conservative: it only says 在招 when it finds an author
reply or explicit text. Everything else is 无法确认. The agent can refine
low-confidence rows later.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.extract import flatten_comments, source_url  # noqa: E402
from product_intern_daily.normalize import extract_emails  # noqa: E402
from product_intern_daily.filters import buy_flags, closed_flags, is_help_seeking, referral_code  # noqa: E402

BJ = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 3, tzinfo=BJ)
BASE = Path(__file__).resolve().parents[1]
OCR_DIR = Path(os.environ.get("OCR_DIR", "data/ocr100"))
if not OCR_DIR.is_absolute():
    OCR_DIR = BASE / OCR_DIR

KNOWN = [
    ("字节跳动", ["字节跳动", "字节", "bytedance", "ByteDance"]),
    ("腾讯", ["腾讯", "tencent", "鹅厂", "微信", "IEG", "WXG"]),
    ("阿里巴巴", ["阿里巴巴", "阿里", "alibaba", "千问", "淘天", "蚂蚁"]),
    ("美团", ["美团", "meituan"]),
    ("百度", ["百度", "baidu", "熊厂"]),
    ("快手", ["快手", "kuaishou", "ks"]),
    ("小红书", ["小红书", "xiaohongshu", "rednote"]),
    ("京东", ["京东", "jd.com", "京东零售"]),
    ("滴滴", ["滴滴", "didi"]),
    ("华为", ["华为", "huawei"]),
    ("小米", ["小米", "xiaomi"]),
    ("网易", ["网易", "netease"]),
    ("哔哩哔哩", ["哔哩哔哩", "B站", "bilibili"]),
    ("Shopee", ["Shopee", "虾皮"]),
    ("SHEIN", ["SHEIN", "希音"]),
    ("科大讯飞", ["科大讯飞", "讯飞", "iflytek"]),
    ("月之暗面", ["月之暗面", "Moonshot", "Kimi"]),
    ("智谱", ["智谱", "Zhipu", "GLM"]),
    ("MiniMax", ["MiniMax", "稀宇"]),
    ("商汤", ["商汤", "SenseTime"]),
    ("拼多多", ["拼多多", "PDD"]),
    ("携程", ["携程", "Trip.com"]),
    ("得物", ["得物", "Poizon"]),
    ("蔚来", ["蔚来", "NIO"]),
    ("理想", ["理想汽车", "理想"]),
    ("小鹏", ["小鹏", "XPeng"]),
    ("海尔", ["海尔", "Haier"]),
    ("美的", ["美的", "Midea"]),
    ("大疆", ["大疆", "DJI"]),
    ("OPPO", ["OPPO"]),
    ("vivo", ["vivo"]),
    ("荣耀", ["荣耀", "HONOR"]),
    ("联想", ["联想", "Lenovo"]),
]

DOMAIN_MAP = {
    "bytedance.com": "字节跳动", "tencent.com": "腾讯", "baidu.com": "百度",
    "alibaba-inc.com": "阿里巴巴", "kuaishou.com": "快手", "jd.com": "京东",
    "apple.com": "Apple", "iflytek.com": "科大讯飞", "duxiaoman.com": "度小满",
    "xiaohongshu.com": "小红书", "meituan.com": "美团", "didiglobal.com": "滴滴",
    "minimax.io": "MiniMax", "moonshot.cn": "月之暗面", "zhipuai.cn": "智谱",
    "one2x.ai": "One2X", "arkevo.ai": "Arkevo", "sparclab.ai": "Sparclab",
    "pyra.io": "PYRA", "philoai.com": "Philo AI",
}

CITIES = ["北京", "上海", "深圳", "杭州", "广州", "成都", "武汉", "南京", "苏州", "西安",
          "合肥", "长沙", "青岛", "厦门", "重庆", "天津", "无锡", "佛山", "东莞", "珠海",
          "香港", "新加坡", "美国", "远程"]
CLOSURE = ["已招到", "已招满", "已截止", "不收了", "不收啦", "停止招聘", "停招", "招满",
           "简历已筛完", "先不投", "不用投", "已找到", "已下线", "岗位关闭"]
ACTIVE = ["没删就还在", "没删就是在招", "还在招", "还在", "继续招", "招", "可以投", "可以～",
          "可以", "有", "在的", "还在收"]
NOISE = ["面经", "凉经", "一面", "二面", "三面", "复盘", "值不值得", "如何找到", "教程",
         "SOP", "求职", "求实习", "选offer", "offer比较", "上岸", "实习体验", "实习总结",
         "行业讨论", "秋招强度", "经验分享", "壁垒", "避雷", "建议", "千万别", "一定要", "劝退", "怎么选", "值得去", "值得吗", "面试", "0 面试", "0面试", "offer", "接了", "圆满结束", "有来的吗", "有去的吗", "怎么样", "求问", "请问", "简历求", "求修改", "求助", "路径", "收好", "转行", "转ai", "背景", "为什么", "普及", "身位", "社招要", "达到的", "盘点", "揭秘", "一文", "攻略", "指南", "告诉你", "belike", "勇闯", "做游戏", "0经验", "想问问", "如何", "感受", "主投", "面经", "复盘", "吐槽", "经验分享"]
HIRE = ["招", "招聘", "内推", "继任", "hc", "岗位", "急招", "捞人", "求继任", "邮箱"]
CONVERT = ["可转正", "转正hc", "有转正", "转正机会", "转正名额", "留用", "表现优秀可转正"]
NO_CONVERT = ["无转正", "没有转正", "不提供转正", "不转正", "无hc", "没有hc"]
AGENCY = ["不限专业", "零经验", "0经验", "包过", "培训", "付费", "有偿", "内推费", "名额有限",
          "速冲", "简历直推", "大厂内推", "保offer", "求职辅导"]


def days_ago(ms: int | float | None) -> int:
    if not ms:
        return 9999
    return (NOW - datetime.fromtimestamp(float(ms) / 1000, BJ)).days


def find_company(text: str, emails: list[str] | None = None) -> str:
    for e in emails or []:
        domain = e.split("@")[-1].lower()
        for d, name in DOMAIN_MAP.items():
            if domain == d or domain.endswith("." + d):
                return name
    low = text.lower()
    hits = []
    for name, keys in KNOWN:
        for k in keys:
            if k.lower() in low:
                hits.append((len(k), name))
                break
    if hits:
        hits.sort(reverse=True)
        return hits[0][1]
    m = re.search(r"(?:公司|企业|团队)[:：]\s*([^\n，,。;；]{2,20})", text)
    if m:
        return m.group(1).strip()
    return "未识别"


def find_location(text: str) -> str:
    m = re.search(r"(?:base|地点|坐标|工作地点)[:：]?\s*(北京|上海|深圳|杭州|广州|成都|武汉|南京|苏州|西安|合肥|长沙|青岛|厦门|重庆|天津|无锡|佛山|东莞|珠海|香港|新加坡|美国|远程)", text, re.I)
    if m:
        return m.group(1)
    found = []
    for c in CITIES:
        if c in text and c not in found:
            found.append(c)
    if "远程" in found:
        return "远程"
    return " / ".join(found[:2]) if found else "待确认"


def employment_type(text: str) -> str:
    if "日常实习" in text:
        return "日常实习"
    if any(k in text for k in ("寒假实习", "暑期实习")):
        return "寒假/暑期实习"
    if "实习" in text:
        return "实习"
    if any(k in text for k in ("校招", "27届", "28届", "2027", "2028")):
        return "校招"
    if any(k in text for k in ("全职", "社招", "正职")):
        return "正职"
    return "未知"


def salary(text: str) -> str:
    m = re.search(r"(\d+\s*[-~—]\s*\d+\s*(?:元/天|/天|k|K|万))", text)
    if m:
        return m.group(1).replace(" ", "")
    m = re.search(r"(\d+\s*(?:元/天|/天))", text)
    return m.group(1) if m else ""


def clean_position(title: str, company: str = "") -> str:
    t = re.sub(r"#.*$", "", title).strip()
    t = re.sub(r"[【】\[\]]", "", t)
    t = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]", "", t)
    if company and company != "未识别":
        for name, keys in KNOWN:
            if name == company:
                for k in keys:
                    t = re.sub(re.escape(k), "", t, flags=re.I)
                t = re.sub(re.escape(name), "", t)
                break
    t = re.sub(r"^\s*(急招|急聘|招人|招聘|内推|找继任|招继任|求继任)\s*", "", t)
    t = re.sub(r"(base|地点|坐标)[:：]?\s*(北京|上海|深圳|杭州|广州|成都|武汉|南京|苏州|西安|合肥|长沙|青岛|厦门|重庆|天津|无锡|佛山|东莞|珠海|香港|新加坡|美国|远程)", "", t, flags=re.I)
    t = re.sub(r"(北京|上海|深圳|杭州|广州|成都|武汉|南京|苏州|西安|合肥|长沙|青岛|厦门|重庆|天津|无锡|佛山|东莞|珠海|香港|新加坡|美国|远程)", "", t)
    t = re.sub(r"(寒假|暑期|日常|春招|秋招|27届|28届|29届|2027|2028|2029|留学生|可预约|开招啦|开招|招募中|正在招募)", "", t)
    t = re.sub(r"\d+\s*[-~—]\s*\d+\s*(?:元/天|/天|k|K|万)", "", t)
    t = re.sub(r"\d+\s*(?:元/天|/天)", "", t)
    t = re.sub(r"(找继任啦|找继任|招继任|求继任|有转正HC|有HC|可转正|继任)", "", t, flags=re.I)
    t = re.sub(r"^\d{1,2}[.\-/]\d{1,2}\s*", "", t)
    t = re.sub(r"^(主站|首页|商业化|业务|部门)[-—]?", "", t)
    t = re.sub(r"^招", "", t)
    t = re.sub(r"[!！~～]+", "", t)
    t = re.sub(r"\s+", " ", t).strip(" -—|·:：,，。")
    roles = ["产品", "产运", "运营", "设计", "算法", "开发", "工程", "市场", "数据", "项目",
             "策略", "商业化", "增长", "内容", "测试", "研究", "分析", "AI", "大模型", "Agent"]
    parts = [p.strip(" -—|·:：,，。") for p in re.split(r"[｜|丨/：:\-—]", t) if p.strip()]
    picked = [p for p in parts if any(r.lower() in p.lower() for r in roles)]
    if picked:
        t = max(picked, key=len)
    if not any(r.lower() in t.lower() for r in roles):
        return "未识别（见正文）"
    return t[:80] or "未识别（见正文）"

def status_of(detail: dict, text: str) -> tuple[str, str, str, bool]:
    """Return (status, evidence, reason, closed). Status is only 在招/无法确认."""
    comments = flatten_comments(detail)
    comments.sort(key=lambda c: c.get("created_at") or "")
    for kw in closed_flags(text):
        return "无法确认", f"正文/标题出现“{kw}”", f"检测到截止信号：{kw}", True
    for c in reversed(comments):
        if not c.get("is_author") or not c.get("content"):
            continue
        content = c["content"]
        for kw in closed_flags(content):
            return "无法确认", f"作者 {c.get('created_at','')[:10]} 回复：{content[:80]}", "作者确认截止", True
        for kw in ACTIVE:
            if kw in content:
                return "在招", f"作者 {c.get('created_at','')[:10]} 回复：{content[:80]}", "作者确认在招", False
    return "无法确认", "", "未找到作者在招/截止的明确回复", False

def is_job(title: str, desc: str, emails: list[str]) -> bool:
    t = (title + "\n" + desc[:600]).lower()
    tl = re.sub(r"(秋招|校招|春招|招生|社招)", "", title.lower())
    if any(k.lower() in tl for k in NOISE) and not any(k.lower() in tl for k in HIRE):
        return False
    if re.search(r"(如何|想问|有人愿意|有来的吗|吗[？?]?)", tl) and not any(k in tl for k in ("招", "招聘", "内推")):
        return False
    if not any(k.lower() in t for k in HIRE):
        return False
    if len(desc.strip()) < 40 and not emails:
        return False
    return True


def extract(detail: dict) -> dict:
    note = (detail.get("data") or {}).get("note") or {}
    post_id = note.get("noteId") or ""
    title = note.get("title", "") or ""
    desc = note.get("desc", "") or ""
    comments = flatten_comments(detail)
    comment_text = "\n".join(c.get("content", "") for c in comments)
    ocr = detail.get("_ocr", "") or ""
    ocr_path = OCR_DIR / f"{post_id}.txt"
    if not ocr and ocr_path.exists():
        ocr = ocr_path.read_text(encoding="utf-8", errors="ignore")
    text = title + "\n" + desc + "\n" + comment_text + "\n" + ocr
    body_emails = extract_emails(desc)
    comment_emails = extract_emails(comment_text)
    ocr_emails = extract_emails(ocr)
    emails = list(dict.fromkeys(body_emails + comment_emails + ocr_emails))
    email_source = "/".join(x for x, ok in [("正文", body_emails), ("评论", comment_emails), ("图片OCR", ocr_emails)] if ok)
    company = find_company(title + "\n" + desc + "\n" + ocr, emails)
    position = clean_position(title, company)
    location = find_location(title + "\n" + desc + "\n" + comment_text)
    etype = employment_type(title + "\n" + desc)
    sal = salary(text)
    status, evidence, sreason, closed = status_of(detail, title + "\n" + desc)
    buy = buy_flags(comment_text)
    help_seek = is_help_seeking(title + "\n" + desc + "\n" + comment_text)
    referral = referral_code(title + "\n" + desc + "\n" + comment_text)
    pinned = next((c.get("content") for c in comments if c.get("pinned") and c.get("content")), "")
    low = text.lower()
    no_conv = [k for k in NO_CONVERT if k in low]
    conv_hits = [k for k in CONVERT if k in low]
    convertible = bool(conv_hits) and not no_conv
    conversion_evidence = ("出现：" + "、".join(conv_hits[:2])) if convertible else ("明确无转正：" + "、".join(no_conv[:2]) if no_conv else "未出现转正相关表述")
    job = is_job(title, desc, emails) and not buy and not help_seek
    age = days_ago(note.get("time"))
    agency = any(k in desc for k in AGENCY)
    contact = ""
    for kw in ("私信", "扫码", "内推码", "微信", "邮箱", "官网", "BOSS"):
        if kw in desc:
            contact = kw
            break
    confidence = 0.5
    if emails:
        confidence += 0.15
    if status == "在招":
        confidence += 0.2
    if company != "未识别":
        confidence += 0.1
    if location != "待确认":
        confidence += 0.05
    if agency:
        confidence -= 0.2
    confidence = round(max(0.05, min(0.95, confidence)), 2)
    reason = []
    if job:
        reason.append("标题/正文含招聘词")
        if emails:
            reason.append("有邮箱")
        if status == "在招":
            reason.append("作者确认在招")
        if agency:
            reason.append("疑似内推/广告，需核实")
    else:
        reason.append("非招聘/经验/个人求职帖")
    return {
        "post_id": post_id,
        "is_job_post": job,
        "company": company,
        "position": position,
        "email": emails,
        "contact": contact,
        "location": location,
        "employment_type": etype,
        "salary": sal,
        "still_hiring": status if job else "无法确认",
        "status_evidence": evidence if job else "",
        "confidence": confidence,
        "reason": "；".join(reason) + f"（发布 {age} 天前）",
        "description": desc[:1000],
        "published_at": note.get("time"),
        "source_url": source_url(post_id, note.get("xsecToken", "")),
        "ocr_text": ocr,
        "comments": comments,
        "comment_email": ";".join(comment_emails),
        "email_source": email_source,
        "base_location": location,
        "referral_code": referral,
        "pinned_comment": pinned,
        "closed": closed,
        "convertible": convertible,
        "conversion_evidence": conversion_evidence,
        "buy_flags": buy,
        "help_seeking": help_seek,
        "excluded_reason": ("评论区购买/表格" if buy else "求助/职业咨询帖" if help_seek else ""),
    }


def main():
    details_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "data/details100")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "data/extractions100.json")
    rows = []
    for p in sorted(details_dir.glob("*.json")):
        try:
            detail = json.loads(p.read_text(encoding="utf-8"))
            rows.append(extract(detail))
        except Exception as exc:
            print(f"skip {p.name}: {exc}", file=sys.stderr)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    jobs = sum(1 for r in rows if r["is_job_post"])
    emails = sum(1 for r in rows if r["email"])
    active = sum(1 for r in rows if r["still_hiring"] == "在招")
    print(json.dumps({"total": len(rows), "job_posts": jobs, "with_email": emails, "active": active, "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
