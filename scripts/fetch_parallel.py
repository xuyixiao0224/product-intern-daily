#!/usr/bin/env python3
import json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.mcp_client import MCPClient

cands = json.load(open(sys.argv[1]))["candidates"]
out = Path(sys.argv[2] if len(sys.argv) > 2 else "data/details100")
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 100
workers = int(sys.argv[4]) if len(sys.argv) > 4 else 3
out.mkdir(parents=True, exist_ok=True)
todo = []
for c in cands[:limit]:
    pid = c.get("id") or c.get("post_id")
    if not pid:
        continue
    p = out / f"{pid}.json"
    if p.exists() and p.stat().st_size > 500:
        continue
    todo.append((pid, c.get("xsec_token") or c.get("token") or "", p))
print(f"todo {len(todo)} / {min(len(cands), limit)} (workers={workers})", flush=True)
lock = threading.Lock()
done = err = 0

def work(item):
    pid, tok, path = item
    time.sleep(0.5)
    for attempt in (1, 2):
        try:
            d = MCPClient().detail(pid, tok)
            path.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            return pid, True, ""
        except Exception as exc:
            if attempt == 2:
                return pid, False, str(exc)
            time.sleep(3)
    return pid, False, "unknown"

with ThreadPoolExecutor(max_workers=workers) as ex:
    futs = [ex.submit(work, it) for it in todo]
    for i, f in enumerate(as_completed(futs), 1):
        pid, ok, msg = f.result()
        with lock:
            if ok:
                done += 1
            else:
                err += 1
            print(f"[{i}/{len(todo)}] {'ok' if ok else 'err'} {pid} {msg[:80]}", flush=True)
print(json.dumps({"ok": done, "err": err, "out": str(out)}, ensure_ascii=False))
