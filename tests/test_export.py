import tempfile
import unittest
from pathlib import Path

from product_intern_daily.export import dedup_jobs, export_csv, export_html, export_json, summary
from product_intern_daily.models import Job


class ExportTest(unittest.TestCase):
    def jobs(self):
        return [
            Job(post_id="p1", company="A", position="AI产品实习", email="hr@x.com", still_hiring="在招", published_at="2026-11-01T00:00:00+08:00", dedup_key="email:hr@x.com"),
            Job(post_id="p2", company="A", position="AI产品实习", email="hr@x.com", still_hiring="在招", published_at="2026-11-02T00:00:00+08:00", dedup_key="email:hr@x.com"),
            Job(post_id="p3", company="B", position="产品实习", email="", still_hiring="无法确认", published_at="2026-11-03T00:00:00+08:00", dedup_key="note:p3"),
        ]

    def test_dedup_keeps_newest_with_email(self):
        rows = dedup_jobs(self.jobs())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].post_id, "p3")  # newest first
        self.assertEqual({r.post_id for r in rows}, {"p2", "p3"})

    def test_summary(self):
        s = summary(self.jobs())
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["with_email"], 2)
        self.assertEqual(s["emails"], 1)

    def test_export_files(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(export_csv(self.jobs(), Path(d) / "jobs.csv"), 2)
            self.assertEqual(export_html(self.jobs(), Path(d) / "jobs.html"), 2)
            self.assertIn("A", (Path(d) / "jobs.html").read_text(encoding="utf-8"))
            self.assertEqual(len((Path(d) / "jobs.csv").read_text(encoding="utf-8-sig").strip().splitlines()), 3)
            self.assertEqual(export_json(self.jobs(), Path(d) / "jobs.json"), 2)


if __name__ == "__main__":
    unittest.main()
