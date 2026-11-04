import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from dashboard_data import aggregate, build_stats, recorded_date
from build_readme_charts import render_svg
from update_readme_table import render_jobs_block
from update_readme_dashboard import render_dashboard
from merge_jobs import merge_records


def job(pid, day, **kw):
    return {"post_id": pid, "first_seen_at": day, "published_at": "2026-11-04", "source_url": "https://example.com/" + pid, "company": "测试", "position": "产品实习", **kw}


class DashboardTest(unittest.TestCase):
    def test_new_vs_pool_identity(self):
        jobs = [job("old", "2026-11-03", still_hiring="在招"), job("new", "2026-11-04"), job("closed", "2026-11-04", closed=True)]
        stats = build_stats(jobs)
        self.assertEqual((stats["previous_total"], stats["new"], stats["total"]), (1, 2, 3))
        self.assertEqual(sum(r["new"] for r in stats["by_date"]), stats["total"])
        self.assertEqual((stats["active"], stats["uncertain"], stats["closed"]), (1, 1, 1))
        # A republication today does not make an earlier record new.
        self.assertEqual(recorded_date(jobs[0]), "2026-11-03")
        block = render_jobs_block(jobs)
        self.assertIn("本期新增 · 1", block)
        self.assertIn("往期岗位 · 1", block)
        self.assertIn("本期另有 1 条已截止", block)
        for j in jobs:
            self.assertEqual(block.count('https://example.com/' + j['post_id'] + ')'), 2)

    def test_reporting_cutoff_excludes_later_jobs(self):
        jobs = [job("old", "2026-11-02"), job("yesterday", "2026-11-03"), job("today", "2026-11-04")]
        stats = build_stats(jobs, "2026-11-03")
        self.assertEqual((stats["previous_total"], stats["new"], stats["total"]), (1, 1, 2))
        self.assertEqual(stats["later_total"], 1)
        self.assertEqual(stats["source_total"], 3)
        self.assertEqual(len(stats["by_date"]), 2)
        self.assertNotIn("https://example.com/today)", render_jobs_block(jobs, "2026-11-03"))

    def test_merge_preserves_first_seen_and_counts_old_posts_when_collected(self):
        old = job("a", "2026-11-03", email="a@example.com", still_hiring="在招")
        update = job("a", "2026-11-04", email="a@example.com", still_hiring="在招")
        incoming = job("b", "2025-01-01", email="b@example.com")
        now = "2026-11-04T20:00:00+08:00"
        merged = merge_records([old], [update, incoming], now)
        self.assertEqual(next(j for j in merged if j["post_id"] == "a")["first_seen_at"], "2026-11-03")
        self.assertEqual(next(j for j in merged if j["post_id"] == "b")["first_seen_at"], now)
        self.assertEqual(build_stats(merged)["new"], 1)
        closed = merge_records([old], [{**update, "closed": True, "still_hiring": "无法确认"}], now)
        self.assertTrue(closed[0]["closed"])
        self.assertEqual(closed[0]["first_seen_at"], "2026-11-03")

    def test_timezone_and_week_year_boundary(self):
        self.assertEqual(recorded_date(job("a", "2026-11-03T23:30:00Z")), "2026-11-04")
        rows = [{"date": "2025-12-29", "new": 2, "total": 2}, {"date": "2026-01-02", "new": 3, "total": 5}, {"date": "2026-01-05", "new": 4, "total": 9}]
        weekly = aggregate(rows, "week")
        self.assertEqual([r['new'] for r in weekly], [5, 4])
        self.assertEqual([r['total'] for r in weekly], [5, 9])
        self.assertEqual([r['new'] for r in aggregate(rows, "month")], [2, 7])
        self.assertEqual(len(aggregate(rows, "day")), 3)  # No fake zero days.

    def test_readme_embeds_native_controls_not_external_page(self):
        block = render_dashboard(build_stats([job("a", "2026-11-04")]))
        self.assertEqual(block.count("<picture>"), 3)
        self.assertEqual(block.count("<details open>"), 1)
        self.assertNotIn("dashboard.html", block)
        self.assertNotIn("<iframe", block)
        self.assertNotIn("<script", block)
        self.assertNotIn("| 指标", block)

    def test_empty_and_single_point_charts_are_valid(self):
        for jobs in [[], [job("a", "2026-11-04")]]:
            stats = build_stats(jobs, "2026-11-04")
            for mode in ["day", "week", "month"]:
                for theme in ["light", "dark"]:
                    for compact in [False, True]:
                        svg = render_svg(stats, mode, theme, compact)
                        ET.fromstring(svg)
                        self.assertNotIn("nan", svg)
                        self.assertNotIn("<script", svg)


if __name__ == "__main__":
    unittest.main()
