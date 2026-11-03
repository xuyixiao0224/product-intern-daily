"""Command line interface for product-intern-daily."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import DEFAULT_MCP_URL, resolve_db
from .export import dedup_jobs, export_csv, export_html, export_json, summary
from .extract import import_extractions, prepare_tasks
from .mcp_client import MCPClient, MCPError
from .models import now_iso
from .ocr import has_ocr, ocr_detail
from .store import Store


def _since(value: str | None) -> str | None:
    if not value:
        return None
    m = re.fullmatch(r"(\d+)d", value.strip())
    if m:
        dt = datetime.now(timezone.utc) - timedelta(days=int(m.group(1)))
        return dt.astimezone().isoformat(timespec="seconds")
    return value


def _load_candidates(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("candidates", [])
    if not isinstance(data, list):
        raise SystemExit("candidates file must be a JSON list or {'candidates': [...]}")
    return data


def _ask(prompt, default):
    try:
        value = input(f"{prompt} [{default}]: ").strip()
    except EOFError:
        value = ""
    return value or default


def cmd_init(args) -> int:
    out = Path(args.dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    if args.yes:
        role, base, when, ocr = "产品", "不限", "一周内", True
    else:
        role = "产品"
        when = _ask("时间范围（一天内/一周内/半年内）", "一周内")
        ocr = _ask("启用本地 OCR（yes/no）", "yes").lower().startswith("y")
    # 每日固定 3 个关键词；Base 只作为提示，不拼接成搜索矩阵
    keywords = ["产品实习", "产品继任", "互联网产品"]
    run = out / "run.sh"
    if run.exists() and not args.force:
        print(f"refuse to overwrite {run}; use --force", file=sys.stderr)
        return 1
    ocr_flag = " --ocr" if ocr else ""
    run.write_text(f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 run.py doctor
python3 run.py search {' '.join(f'--keyword "{k}"' for k in keywords)} --sort 最新 --publish-time {when} --note-type 图文 --out candidates.json
python3 run.py fetch candidates.json --out details{ocr_flag}
python3 run.py extract --details details --out tasks.json --prepare
echo "下一步：让 Codex/DSH 读 tasks.json，按 prompts/extract.md 写 extractions.json"
echo "然后：python3 run.py extract --import-file extractions.json --details details"
""", encoding="utf-8")
    run.chmod(0o755)
    (out / "config.yaml").write_text(
        "keywords:\n" + "".join(f"  - \"{k}\"\n" for k in keywords) +
        f"search:\n  publish_time: \"{when}\"\n  sort: \"最新\"\n  note_type: \"图文\"\n"
        f"ocr:\n  enabled: {str(ocr).lower()}\n", encoding="utf-8")
    (out / ".env.example").write_text(
        "# 邮件发送：不要用私人 Gmail/QQ\n"
        "RESEND_API_KEY=\nDIGEST_FROM=digest@yourdomain.com\nDIGEST_WEBHOOK_URL=\n", encoding="utf-8")
    print(json.dumps({"ok": True, "run": str(run), "keywords": keywords, "ocr": ocr, "time": when}, ensure_ascii=False, indent=1))
    if ocr and not has_ocr():
        print("注意：未安装 ocrmac，先运行 pip install -e '.[ocr]'", file=sys.stderr)
    return 0


def cmd_doctor(args) -> int:
    print(f"db: {resolve_db(args.db)}")
    if has_ocr():
        print("ocr: available (local Apple Vision via ocrmac)")
    else:
        print("ocr: NOT installed — run: pip install -e '.[ocr]'")
    client = MCPClient(args.mcp_url)
    try:
        info = client.initialize()
        print(f"mcp: ok ({info.get('serverInfo', {}).get('name', 'unknown')})")
        login = client.check_login()
        print("login:", login.replace("\n", " | "))
        return 0 if "已登录" in login else 1
    except MCPError as exc:
        print(f"mcp: FAILED — {exc}")
        print("hint: start xiaohongshu-mcp and scan the login QR first")
        return 1


def cmd_search(args) -> int:
    client = MCPClient(args.mcp_url)
    started = now_iso()
    keywords = args.keyword or ["产品实习", "产品继任", "互联网产品"]
    if args.base:
        keywords = [f"{k} {args.base}".strip() for k in keywords]
    seen, out, errors = set(), [], []
    for i, keyword in enumerate(keywords):
        if i:
            time.sleep(args.sleep)
        try:
            items = client.search(
                keyword,
                limit=args.limit,
                sort_by=args.sort,
                publish_time=args.publish_time,
                note_type=args.note_type,
            )
            for it in items:
                if it.post_id in seen:
                    continue
                seen.add(it.post_id)
                out.append(it.to_dict())
            print(f"[ok] {keyword}: {len(items)} hits, {len(out)} unique", file=sys.stderr)
        except MCPError as exc:
            errors.append(f"{keyword}: {exc}")
            print(f"[err] {keyword}: {exc}", file=sys.stderr)
    payload = {"keywords": keywords, "count": len(out), "errors": errors, "candidates": out}
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(out)} candidates)", file=sys.stderr)
    else:
        print(text)
    with Store(resolve_db(args.db)) as store:
        store.record_run("search", started, {"count": len(out), "errors": len(errors)})
    return 0 if not errors else 1


def cmd_fetch(args) -> int:
    if args.ocr and not has_ocr():
        print("error: --ocr requires ocrmac (local Apple Vision).", file=sys.stderr)
        print("install: pip install -e '.[ocr]'  (macOS only)", file=sys.stderr)
        return 2
    client = MCPClient(args.mcp_url)
    candidates = _load_candidates(args.input)
    if args.limit:
        candidates = candidates[: args.limit]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = now_iso()
    ok = skipped = err = 0
    for i, c in enumerate(candidates, 1):
        post_id = c.get("post_id") or c.get("id")
        token = c.get("token") or c.get("xsec_token") or ""
        if not post_id:
            err += 1
            continue
        path = out_dir / f"{post_id}.json"
        if path.exists() and path.stat().st_size > 500 and not args.force:
            skipped += 1
            continue
        try:
            detail = client.detail(post_id, token, all_comments=args.all_comments)
            if args.ocr:
                text, paths = ocr_detail(detail, args.images_dir)
                detail["_ocr"] = text
                detail["_images"] = paths
            path.write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
            with Store(resolve_db(args.db)) as store:
                store.mark_seen(post_id, fetched=True)
            ok += 1
            print(f"[{i}/{len(candidates)}] ok {post_id}", file=sys.stderr)
        except Exception as exc:
            err += 1
            print(f"[{i}/{len(candidates)}] err {post_id}: {exc}", file=sys.stderr)
        time.sleep(args.sleep)
    result = {"ok": ok, "skipped": skipped, "err": err, "out": str(out_dir)}
    print(json.dumps(result, ensure_ascii=False))
    with Store(resolve_db(args.db)) as store:
        store.record_run("fetch", started, result)
    return 0 if err == 0 else 1


def cmd_extract(args) -> int:
    if args.prepare:
        n = prepare_tasks(args.details, args.out, limit=args.limit)
        print(json.dumps({"prepared": n, "out": args.out}, ensure_ascii=False))
        return 0
    if args.import_file:
        with Store(resolve_db(args.db)) as store:
            result = import_extractions(args.import_file, store, details_dir=args.details)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["errors"] == 0 else 1
    print("use --prepare or --import", file=sys.stderr)
    return 2


def cmd_export(args) -> int:
    with Store(resolve_db(args.db)) as store:
        jobs = store.list_jobs(since=_since(args.since), status=args.status, include_rejected=args.include_rejected)
    jobs = dedup_jobs(jobs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    result = {"jobs": len(jobs), **summary(jobs)}
    if "csv" in formats:
        result["csv"] = export_csv(jobs, out / "jobs.csv")
    if "html" in formats:
        result["html"] = export_html(jobs, out / "jobs.html", images_dir=args.images_dir)
    if "json" in formats:
        result["json"] = export_json(jobs, out / "jobs.json")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


def cmd_status(args) -> int:
    with Store(resolve_db(args.db)) as store:
        print(json.dumps(store.stats(), ensure_ascii=False, indent=1))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="product-intern-daily", description="产品实习日报：招聘帖 → 可验证线索")
    p.add_argument("--db", help="SQLite path (default: ./data/jobs.sqlite3)")
    p.add_argument("--mcp-url", default=DEFAULT_MCP_URL)
    sub = p.add_subparsers(dest="command", required=True)

    i = sub.add_parser("init", help="interactive onboarding (inspired by Swelist)")
    i.add_argument("--dir", default=".")
    i.add_argument("--yes", action="store_true")
    i.add_argument("--force", action="store_true")
    i.set_defaults(func=cmd_init)

    d = sub.add_parser("doctor", help="check MCP/login/OCR/DB")
    d.set_defaults(func=cmd_doctor)

    s = sub.add_parser("search", help="search XHS with time filters")
    s.add_argument("--keyword", action="append")
    s.add_argument("--role", default="产品", help="默认关键词的角色词，默认 产品")
    s.add_argument("--base", default="", help="默认关键词的 base 地，如 北京/上海")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--sort", default="最新", choices=["综合", "最新", "最多点赞", "最多评论", "最多收藏"])
    s.add_argument("--publish-time", default="一周内", choices=["不限", "一天内", "一周内", "半年内"])
    s.add_argument("--note-type", default="图文", choices=["不限", "视频", "图文"])
    s.add_argument("--sleep", type=float, default=2.0)
    s.add_argument("--out", help="write candidates JSON here (default: stdout)")
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("fetch", help="fetch detail/comments/images for candidates")
    f.add_argument("input")
    f.add_argument("--out", default="details")
    f.add_argument("--images-dir", default="images")
    f.add_argument("--all-comments", action="store_true")
    f.add_argument("--ocr", action="store_true")
    f.add_argument("--force", action="store_true")
    f.add_argument("--limit", type=int)
    f.add_argument("--sleep", type=float, default=2.0)
    f.set_defaults(func=cmd_fetch)

    e = sub.add_parser("extract", help="prepare tasks for an agent, or import its JSON")
    e.add_argument("--details", default="details")
    e.add_argument("--out", default="tasks.json")
    e.add_argument("--prepare", action="store_true")
    e.add_argument("--import-file", dest="import_file")
    e.add_argument("--limit", type=int)
    e.set_defaults(func=cmd_extract)

    x = sub.add_parser("export", help="export deduplicated CSV/HTML")
    x.add_argument("--format", default="csv,html,json")
    x.add_argument("--out", default="exports")
    x.add_argument("--since", help="1d / 7d / 30d or ISO date")
    x.add_argument("--status", choices=["在招", "已截止", "已招到", "无法确认"])
    x.add_argument("--images-dir", default="images")
    x.add_argument("--include-rejected", action="store_true")
    x.set_defaults(func=cmd_export)

    st = sub.add_parser("status", help="show DB stats")
    st.set_defaults(func=cmd_status)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
