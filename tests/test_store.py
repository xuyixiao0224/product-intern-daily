import tempfile
import unittest
from pathlib import Path

from product_intern_daily.models import Job
from product_intern_daily.store import Store


class StoreTest(unittest.TestCase):
    def test_upsert_list_stats(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(Path(d) / "test.sqlite3") as store:
                job = Job(post_id="p1", title="t", email="hr@x.com", still_hiring="在招", published_at="2026-11-01T00:00:00+08:00", is_job_post=True)
                store.upsert_job(job)
                second = Job(post_id="p1", title="t2", email="hr@x.com", still_hiring="在招", published_at="2026-11-01T00:00:00+08:00", is_job_post=True)
                store.upsert_job(second)
                rows = store.list_jobs()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].title, "t2")
                stats = store.stats()
                self.assertEqual(stats["job_posts"], 1)
                self.assertEqual(stats["with_email"], 1)

    def test_rejected_excluded_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            with Store(Path(d) / "test.sqlite3") as store:
                store.upsert_job(Job(post_id="p1", is_job_post=False))
                self.assertEqual(len(store.list_jobs()), 0)
                self.assertEqual(len(store.list_jobs(include_rejected=True)), 1)


if __name__ == "__main__":
    unittest.main()
