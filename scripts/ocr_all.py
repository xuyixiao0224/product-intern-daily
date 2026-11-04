#!/usr/bin/env python3
"""OCR every image in each note (not just the cover)."""
import argparse, json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from product_intern_daily.ocr import _download, _to_jpeg, ocr_file

ap = argparse.ArgumentParser()
ap.add_argument("--details", default="data/seed/details")
ap.add_argument("--out", default="data/seed/ocr")
ap.add_argument("--covers", default="data/seed/covers_raw")
a = ap.parse_args()
details, out, covers = Path(a.details), Path(a.out), Path(a.covers)
out.mkdir(parents=True, exist_ok=True); covers.mkdir(parents=True, exist_ok=True)
todo=[]
for p in sorted(details.glob("*.json")):
    pid=p.stem
    if (out/f"{pid}.txt").exists() and (out/f"{pid}.txt").stat().st_size>0:
        continue
    try: d=json.loads(p.read_text(encoding="utf-8"))
    except Exception: continue
    imgs=((d.get("data") or {}).get("note") or {}).get("imageList") or []
    urls=[x.get("urlDefault") or x.get("urlPre") for x in imgs]
    urls=[u for u in urls if u]
    if urls: todo.append((pid,urls))

def work(item):
    pid, urls = item
    texts=[]
    ok=True
    for i,url in enumerate(urls):
        raw=covers/f"{pid}_{i}.raw"; jpg=covers/f"{pid}_{i}.jpg"
        if not jpg.exists():
            if not _download(url, raw):
                ok=False; continue
            if not _to_jpeg(raw, jpg):
                ok=False; continue
            raw.unlink(missing_ok=True)
        t=ocr_file(jpg)
        if t: texts.append(t)
    (out/f"{pid}.txt").write_text("\n".join(texts), encoding="utf-8")
    return pid, ok

okn=errn=0
with ThreadPoolExecutor(max_workers=3) as ex:
    for i,f in enumerate(as_completed([ex.submit(work,x) for x in todo]),1):
        try:
            _, ok=f.result(); okn+=1 if ok else 0; errn+=0 if ok else 1
            print(f"[{i}/{len(todo)}] {'ok' if ok else 'err'}", flush=True)
        except Exception as e:
            errn+=1; print(f"[{i}/{len(todo)}] err {e}", flush=True)
print(json.dumps({"ok": okn, "err": errn, "out": str(out)}, ensure_ascii=False))
