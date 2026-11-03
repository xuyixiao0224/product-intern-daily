#!/usr/bin/env python3
import json, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.ocr import _download, _to_jpeg, ocr_file

BASE = Path(__file__).resolve().parents[1]
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--details", default="data/seed/details")
ap.add_argument("--out", default="data/seed/ocr")
ap.add_argument("--covers", default="data/seed/covers_raw")
a = ap.parse_args()
details = BASE / a.details
out = BASE / a.out
covers = BASE / a.covers
out.mkdir(parents=True, exist_ok=True); covers.mkdir(parents=True, exist_ok=True)
todo = []
for p in sorted(details.glob("*.json")):
    pid = p.stem
    if (out / f"{pid}.txt").exists():
        continue
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    imgs = ((d.get("data") or {}).get("note") or {}).get("imageList") or []
    if not imgs:
        continue
    url = imgs[0].get("urlDefault") or imgs[0].get("urlPre") or ""
    if url:
        todo.append((pid, url))
print(f"todo {len(todo)}", flush=True)
done = err = 0

def work(item):
    pid, url = item
    raw = covers / f"{pid}.raw"; jpg = covers / f"{pid}.jpg"
    if not jpg.exists():
        if not _download(url, raw):
            return pid, False, "download"
        if not _to_jpeg(raw, jpg):
            return pid, False, "convert"
        raw.unlink(missing_ok=True)
    text = ocr_file(jpg)
    (out / f"{pid}.txt").write_text(text, encoding="utf-8")
    return pid, bool(text), ""

with ThreadPoolExecutor(max_workers=3) as ex:
    futs = [ex.submit(work, x) for x in todo]
    for i, f in enumerate(as_completed(futs), 1):
        pid, ok, msg = f.result()
        done += 1 if ok else 0; err += 0 if ok else 1
        print(f"[{i}/{len(todo)}] {'ok' if ok else 'skip'} {pid} {msg}", flush=True)
print(json.dumps({"ok": done, "err": err, "out": str(out)}, ensure_ascii=False))
