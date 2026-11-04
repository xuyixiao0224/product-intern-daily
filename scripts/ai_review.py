#!/usr/bin/env python3
"""AI second-pass review over already-fetched notes (no crawling)."""
import argparse, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PROMPT = """你是产品实习招聘信息审核员。根据帖子标题、正文、评论、OCR，输出严格 JSON（不要 markdown）。
判断：
1. 是否真实的产品实习岗位：产品经理、产品运营、产品策划、产品设计、产品体验设计、策略产品、AI产品、产品助理；零售/商品方向的产品搭配、竞品陈列调研、VM、商品企划，如果帖子明确是“产品”相关实习也算；但“产品营销/产品市场/品牌 PR”不算产品岗，除非岗位职责明确是产品经理/产品运营/产品策划/产品设计。
2. 公司名：优先正文明确的公司/品牌；没有写就 null，不要猜。
3. 岗位名：清洗成纯净岗位名，去掉“快来快来当我的继任吧”“组内直推”“急招”等标题话术。
4. 邮箱：只输出文本/评论/任意图片 OCR 中明确出现的邮箱，没有就 null；邮箱域名可辅助判断公司（baidu.com→百度，kuaishou.com→快手，tencent.com→腾讯），但正文公司优先。
5. 是否在招：作者回复/正文明确说还在招 -> 在招；已截止/先不投 -> 已截止；否则无法确认。
6. 是否可转正：明确可转正/转正HC/留用 -> true；明确无转正/无HC -> false；否则 false。
7. verdict：通过/不通过；不通过要写原因（非产品岗/非招聘/已截止/引流/无有效信息）。
8. 投递方式：必须存在真实邮箱，或明确“私信/扫码/简历发我/联系我”；只有“投递”两个字不算有效投递方式。

输出：
{"is_product":true,"verdict":"通过","company":"...","position":"...","base":"...","email":"...","still_hiring":"在招","convertible":false,"reason":"...","confidence":0.0}
"""
KNOWN = ["萨洛蒙", "Salomon", "亚玛芬", "欧莱雅", "科颜氏", "Kiehl", "帆软", "滴滴", "腾讯", "百度", "字节跳动", "快手", "阿里巴巴", "美团", "小红书", "小米", "爱奇艺", "网易", "京东", "OPPO", "科大讯飞"]


def load_key():
    p = Path("../xhs-job-monitor/.env.local")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("LLM_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("LLM_API_KEY", "")


def call(prompt, key, base, model):
    payload = json.dumps({"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=payload, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        obj = json.loads(r.read())
    text = obj["choices"][0]["message"]["content"].strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--details", default="data/daily/2026-11-04/details")
    ap.add_argument("--extractions", default="data/daily/2026-11-04/extractions.json")
    ap.add_argument("--ocr", default="data/daily/2026-11-04/ocr")
    ap.add_argument("--out", default="data/review/ai_2026-11-04.json")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    key = load_key()
    if not key:
        sys.exit("LLM_API_KEY missing")
    base = os.environ.get("LLM_API_BASE", "https://api.deepseek.com/v1")
    model = os.environ.get("LLM_MODEL", "deepseek-chat")
    exs = json.loads(Path(args.extractions).read_text(encoding="utf-8"))
    if args.limit: exs = exs[:args.limit]
    details = Path(args.details); ocr = Path(args.ocr)
    tasks = []
    for e in exs:
        d = json.loads((details / f"{e['post_id']}.json").read_text(encoding="utf-8"))
        n = (d.get("data") or {}).get("note") or {}
        comments = "\n".join(str(c.get("content") or "") for c in (e.get("comments") or [])[:8])
        ot = (ocr / f"{e['post_id']}.txt")
        ocr_text = ot.read_text(errors="ignore") if ot.exists() else ""
        prompt = PROMPT + f"\n\n标题：{n.get('title','')}\n正文：{(n.get('desc') or '')[:2000]}\n评论：{comments[:1500]}\nOCR：{ocr_text[:1500]}\n已知候选公司：{', '.join(KNOWN)}"
        tasks.append((e["post_id"], prompt))
    out = []
    def work(item):
        pid, prompt = item
        for attempt in (1, 2):
            try:
                r = call(prompt, key, base, model); r["post_id"] = pid; return r
            except Exception as exc:
                if attempt == 2: return {"post_id": pid, "error": str(exc)}
                time.sleep(2)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for f in as_completed([pool.submit(work, t) for t in tasks]):
            out.append(f.result())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"total": len(out), "errors": sum(1 for x in out if "error" in x), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
