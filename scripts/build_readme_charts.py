#!/usr/bin/env python3
"""Generate self-contained SVG images that GitHub READMEs can render directly."""
import argparse
import html
import json
import math
from pathlib import Path
from dashboard_data import aggregate

THEMES = {
    "light": {"bg": "#ffffff", "fg": "#1f2925", "muted": "#66736c", "line": "#e5eae6", "soft": "#eef2ef", "accent": "#258564", "bar": "#aed6c0", "ink": "#52675b"},
    "dark": {"bg": "#0d1117", "fg": "#e6ede8", "muted": "#98a89e", "line": "#29352e", "soft": "#25322a", "accent": "#6dcba0", "bar": "#375e49", "ink": "#a0b7a8"},
}
LABELS = {"day": "按日", "week": "按周", "month": "按月"}
LIMITS = {"day": 30, "week": 12, "month": 12}


def render_svg(stats, mode="day", theme="light", compact=False):
    p = THEMES[theme]
    rows = aggregate(stats.get("by_date", []), mode)[-LIMITS[mode]:]
    canvas_width, canvas_height = (480, 492) if compact else (900, 452)
    pad, end = (24, 456) if compact else (32, 868)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_width}" height="{canvas_height}" viewBox="0 0 {canvas_width} {canvas_height}" role="img" aria-labelledby="title desc">',
             f'<title id="title">岗位收录趋势 · {LABELS[mode]}</title>',
             f'<desc id="desc">本期 {stats["new"]}，往期 {stats["previous_total"]}，累计 {stats["total"]}。绿色柱为新增，折线为累计。{html.escape(json.dumps(rows, ensure_ascii=False))}</desc>',
             f'<rect x=".5" y=".5" width="{canvas_width-1}" height="{canvas_height-1}" rx="12" fill="{p["bg"]}" stroke="{p["line"]}"/>',
             '<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">']

    def text(x, y, value, size=13, fill=None, weight=400, anchor="start"):
        if compact and size < 16:
            size = 16
        parts.append(f'<text x="{x}" y="{y}" fill="{fill or p["fg"]}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>')

    def line(x1, y1, x2, y2, color=None, **attrs):
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or p["line"]}" {extra}/>')

    text(pad, 33, "岗位收录趋势", 15, weight=600)
    text(end, 33, f'{LABELS[mode]} · 截至 {stats["report_date"]}', 12, p["muted"], anchor="end")
    # One continuous equation makes the relationship visible without a second table.
    metrics = [(pad, "往期 / 未定日期" if stats.get("undated") else "往期已收录", stats["previous_total"] + stats.get("undated", 0), p["fg"]), (190 if compact else 338, f'{stats["report_date"][5:].replace("-", "/")} 新增', stats["new"], p["accent"]), (352 if compact else 650, "历史累计", stats["total"], p["fg"])]
    for x, label, value, color in metrics:
        text(x, 66, label, 12, p["muted"])
        text(x, 108, value, 36, color, 600)
        text(x + max(1, len(str(value))) * 23 + 8, 106, "条", 12, p["muted"])
    text(148 if compact else 265, 96, "+", 24, p["muted"])
    text(314 if compact else 576, 96, "=", 24, p["muted"])
    ratio = stats["new"] / max(stats["total"], 1)
    parts.append(f'<rect x="{pad}" y="130" width="{end-pad}" height="5" rx="2.5" fill="{p["soft"]}"/>')
    if ratio:
        parts.append(f'<rect x="{end - (end-pad) * ratio:.2f}" y="130" width="{(end-pad) * ratio:.2f}" height="5" rx="2.5" fill="{p["accent"]}"/>')
    text(pad, 167, "新增与累计", 12, p["muted"])
    parts.append(f'<rect x="{258 if compact else 662}" y="158" width="10" height="10" rx="2" fill="{p["bar"]}"/>')
    text(276 if compact else 679, 167, "新增", 11, p["muted"])
    line(342 if compact else 746, 163, 362 if compact else 766, 163, p["ink"], stroke_width=2)
    text(369 if compact else 773, 167, "累计", 11, p["muted"])
    left, right, top, bottom = (52, 444, 202, 352) if compact else (68, 830, 202, 352)
    maximum = max([r["total"] for r in rows] + [r["new"] for r in rows] + [1])
    raw_step = maximum / 4
    power = 10 ** math.floor(math.log10(raw_step))
    step = max(1, next(n * power for n in (1, 2, 5, 10) if n * power >= raw_step))
    ceiling = step * 4
    for i in range(5):
        value = ceiling * i / 4
        y = bottom - (bottom - top) * i / 4
        line(left, y, right, y, stroke_dasharray="3 5")
        text(left - 12, y + 4, f"{value:g}", 10, p["muted"], anchor="end")
    if rows:
        gap = (right - left) / len(rows)
        width = min(58, gap * .52)
        points = []
        for i, row in enumerate(rows):
            x = left + gap * (i + .5)
            y = bottom - row["new"] / ceiling * (bottom - top)
            y_total = bottom - row["total"] / ceiling * (bottom - top)
            parts.append(f'<rect x="{x-width/2:.2f}" y="{y:.2f}" width="{width:.2f}" height="{bottom-y:.2f}" rx="3" fill="{p["accent"] if i == len(rows)-1 else p["bar"]}"><title>{row["label"]} 新增 {row["new"]} 条</title></rect>')
            if len(rows) < 16 or i == len(rows)-1:
                label_y = max(top + 12, y - 9)
                label_color = p["accent"]
                if abs(label_y - y_total) < 14 and bottom - y > 28:
                    label_y = y + 20
                    label_color = p["bg"] if i == len(rows)-1 else p["fg"]
                text(round(x, 2), round(label_y, 2), row["new"], 11, label_color, 600, "middle")
            if len(rows) < (5 if compact else 10) or i % max(1, len(rows) // (3 if compact else 6)) == 0 or i == len(rows)-1:
                text(round(x, 2), 377, row["label"], 10, p["muted"], anchor="middle")
            points.append((x, y_total))
        parts.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x,y in points)}" fill="none" stroke="{p["ink"]}" stroke-width="2" stroke-linejoin="round"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{p["bg"]}" stroke="{p["ink"]}" stroke-width="2"/>')
        if rows[-1]["new"] != rows[-1]["total"]:
            text(round(points[-1][0] + 12, 2), round(points[-1][1] - 8, 2), rows[-1]["total"], 12, p["ink"], 600)
    else:
        text(canvas_width / 2, 280, "暂无可统计记录", 14, p["muted"], anchor="middle")
    line(pad, 402, end, 402)
    text(pad, 435 if compact else 429, f'明确在招 {stats["active"]}   ·   待确认 {stats["uncertain"]}   ·   已截止 {stats["closed"]}', 11, p["muted"])
    text(end, 471 if compact else 429, f'仅记录 {len(stats.get("by_date", []))} 个日期 · 不补造历史数据', 11, p["muted"], anchor="end")
    parts.append("</g></svg>")
    return "\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default="data/stats.json")
    ap.add_argument("--out", default="docs/assets")
    args = ap.parse_args()
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for mode in LABELS:
        for theme in THEMES:
            for compact in (False, True):
                suffix = ("-mobile" if compact else "") + ("-dark" if theme == "dark" else "")
                (out / f"trend-{mode}{suffix}.svg").write_text(render_svg(stats, mode, theme, compact), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
