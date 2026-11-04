#!/usr/bin/env python3
"""Embed the chart images in the same README section as new and older jobs."""
import argparse
import json
import re
from pathlib import Path

START = "<!-- DASHBOARD:START -->"
END = "<!-- DASHBOARD:END -->"


def picture(mode, label):
    return f'''<picture>
  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="docs/assets/trend-{mode}-mobile-dark.svg">
  <source media="(max-width: 600px)" srcset="docs/assets/trend-{mode}-mobile.svg">
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/trend-{mode}-dark.svg">
  <img src="docs/assets/trend-{mode}.svg" alt="{label}：柱形为新增岗位，折线为累计收录" width="900">
</picture>'''


def render_dashboard(stats):
    lines = [START, "### 收录趋势", "", "绿色柱看新增，折线看积累。按日、周、月展开查看；周从周一开始。", ""]
    for mode, label, scope in [("day", "按日", "最近 30 个记录日"), ("week", "按周", "最近 12 个记录周"), ("month", "按月", "最近 12 个记录月")]:
        lines += ["<details open>" if mode == "day" else "<details>", f"<summary>{label} · {scope}</summary>", "", picture(mode, label), "", "</details>", ""]
    lines += ["<details>", "<summary>统计口径与更新说明</summary>", "",
              f'截至 **{stats["report_date"]}**：往期 **{stats["previous_total"]}** ＋ 本期新增 **{stats["new"]}** ＋ 日期未记录 **{stats.get("undated", 0)}** ＝ 历史累计 **{stats["total"]}**。本期以日期为准，不把最近一期自动称为「昨日」。', "",
              "- 新增按首次记录日期去重计算；旧岗位更新不再次计数，已截止岗位保留在累计中。",
              "- 本期日期可配置；严格 T-1 时按昨日截止日期生成，新旧分组与图表使用同一个截止日期，后续日期的记录不混入本期。",
              "- 早期导入的记录日期由原帖日期回填，后续按首次收录时间记录。曲线反映本项目收录，不代表平台全量岗位。",
              "- 明确在招与待确认分开统计，未标记截止不等于已确认在招。这里展示的是当前核实状态，非历史每日在招快照。",
              "- 只画已有记录，未记录的日期不补零；当前周、月尚未结束，不能直接与完整周期比较。",
              "- README 不运行 JavaScript；此处为每日自动更新的图形，折叠区无需跳转即可切换统计粒度。", "", "</details>", END]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", default="data/stats.json")
    ap.add_argument("--readme", default="README.md")
    args = ap.parse_args()
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    block = render_dashboard(stats)
    path = Path(args.readme)
    text = path.read_text(encoding="utf-8")
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = text.replace("<!-- JOBS:END -->", "<!-- JOBS:END -->\n\n" + block, 1)
    path.write_text(text, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
