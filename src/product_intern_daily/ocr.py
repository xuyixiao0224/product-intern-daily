"""Optional image download + OCR.

Core package has no hard dependency. If `ocrmac` (Apple Vision) is installed,
`ocr_images` returns text; otherwise it returns an empty string and a warning.
"""
from __future__ import annotations

import shutil
import subprocess
import urllib.request
from pathlib import Path

USER_AGENT = "Mozilla/5.0"


def has_ocr() -> bool:
    try:
        import ocrmac  # noqa: F401
        return True
    except Exception:
        return False


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = resp.read()
        if len(data) < 1000:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def _to_jpeg(src: Path, dest: Path) -> bool:
    sips = shutil.which("sips")
    if not sips:
        return src.exists()
    try:
        subprocess.run([sips, "-s", "format", "jpeg", str(src), "--out", str(dest)], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dest.exists() and dest.stat().st_size > 1000
    except Exception:
        return False


def ocr_file(path: Path) -> str:
    if not has_ocr():
        return ""
    try:
        from ocrmac import ocrmac
        result = ocrmac.OCR(str(path), language_preference=["zh-Hans", "en-US"]).recognize()
        return "\n".join(line[0] for line in result)
    except Exception:
        return ""


def ocr_variants(path: Path) -> str:
    """OCR original + 180° rotation + horizontal/vertical flips, de-duplicated."""
    texts = [ocr_file(path)]
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        variants = {
            "rot180": im.rotate(180),
            "flip_h": im.transpose(Image.FLIP_LEFT_RIGHT),
            "flip_v": im.transpose(Image.FLIP_TOP_BOTTOM),
        }
        for name, v in variants.items():
            vp = path.with_name(path.stem + "_" + name + ".jpg")
            v.save(vp, quality=90)
            texts.append(ocr_file(vp))
    except Exception:
        pass
    seen, lines = set(), []
    for block in texts:
        for line in block.splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                lines.append(line)
    return "\n".join(lines)


def ocr_detail(detail: dict, images_dir: str | Path, *, variants: bool = False) -> tuple[str, list[str]]:
    """Download all imageList images and OCR them. Returns (text, local_paths)."""
    note = (detail.get("data") or {}).get("note") or {}
    post_id = note.get("noteId") or "unknown"
    out_dir = Path(images_dir) / post_id
    out_dir.mkdir(parents=True, exist_ok=True)
    texts: list[str] = []
    paths: list[str] = []
    for i, im in enumerate(note.get("imageList") or []):
        url = im.get("urlDefault") or im.get("urlPre") or ""
        if not url:
            continue
        raw = out_dir / f"{i}.raw"
        jpg = out_dir / f"{i}.jpg"
        if not jpg.exists():
            if not _download(url, raw):
                continue
            if not _to_jpeg(raw, jpg):
                continue
            raw.unlink(missing_ok=True)
        paths.append(str(jpg))
        text = ocr_variants(jpg) if variants else ocr_file(jpg)
        if text:
            texts.append(f"--- image {i} ---\n{text}")
    # Comment images are not always returned by xiaohongshu-mcp; support the
    # common fields when they are present.
    for j, c in enumerate(((detail.get("data") or {}).get("comments") or {}).get("list") or []):
        for key in ("imageList", "pictures", "images"):
            for k, im in enumerate(c.get(key) or []):
                url = im.get("urlDefault") or im.get("urlPre") or im.get("url") or ""
                if not url:
                    continue
                raw = out_dir / f"comment_{j}_{k}.raw"
                jpg = out_dir / f"comment_{j}_{k}.jpg"
                if not jpg.exists():
                    if not _download(url, raw):
                        continue
                    if not _to_jpeg(raw, jpg):
                        continue
                    raw.unlink(missing_ok=True)
                paths.append(str(jpg))
                text = ocr_variants(jpg) if variants else ocr_file(jpg)
                if text:
                    texts.append(f"--- comment {j} image {k} ---\n{text}")
    return "\n".join(texts), paths
