import json
import tempfile
import unittest
from pathlib import Path

from product_intern_daily.extract import build_job, import_extractions, prepare_tasks, validate_extraction


class ExtractTest(unittest.TestCase):
    def detail(self):
        return json.loads(Path(__file__).parent.joinpath("fixtures/detail_sample.json").read_text(encoding="utf-8"))

    def extraction(self):
        return {
            "post_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
            "is_job_post": True,
            "company": "字节跳动",
            "position": "AI产品经理实习生",
            "email": ["HR@Example.com"],
            "contact": "",
            "location": "北京",
            "employment_type": "实习",
            "salary": "500/天",
            "still_hiring": "在招",
            "status_evidence": "作者回复：还在招",
            "confidence": 0.9,
            "reason": "有具体 JD 和作者回复",
        }

    def test_build_job(self):
        job = build_job(self.extraction(), self.detail())
        self.assertEqual(job.email, "hr@example.com")
        self.assertEqual(job.dedup_key, "email:hr@example.com")
        self.assertEqual(job.source_url.split("/explore/")[1].split("?")[0], "aaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(len(job.comments), 2)
        self.assertTrue(job.content_hash)

    def test_old_closed_status_maps(self):
        item = self.extraction()
        item["still_hiring"] = "已截止"
        job = build_job(item, self.detail())
        self.assertEqual(job.still_hiring, "无法确认")
        self.assertTrue(job.closed)

    def test_base_and_referral(self):
        item = self.extraction()
        item["base_location"] = "上海"
        item["referral_code"] = "ABC123"
        job = build_job(item, self.detail())
        self.assertEqual(job.base_location, "上海")
        self.assertEqual(job.referral_code, "ABC123")

    def test_convertible(self):
        item = self.extraction()
        item["convertible"] = True
        item["conversion_evidence"] = "出现：可转正"
        job = build_job(item, self.detail())
        self.assertTrue(job.convertible)
        self.assertEqual(job.conversion_evidence, "出现：可转正")

    def test_invalid_status(self):
        bad = self.extraction()
        bad["still_hiring"] = "在招中"
        with self.assertRaises(ValueError):
            validate_extraction(bad)

    def test_prepare_and_import(self):
        with tempfile.TemporaryDirectory() as d:
            details = Path(d) / "details"
            details.mkdir()
            details.joinpath("a.json").write_text(json.dumps(self.detail()), encoding="utf-8")
            tasks = Path(d) / "tasks.json"
            self.assertEqual(prepare_tasks(details, tasks), 1)
            payload = json.loads(tasks.read_text(encoding="utf-8"))
            self.assertEqual(payload["tasks"][0]["post_id"], "aaaaaaaaaaaaaaaaaaaaaaaa")
            extractions = Path(d) / "extractions.json"
            extractions.write_text(json.dumps([self.extraction()]), encoding="utf-8")
            from product_intern_daily.store import Store
            with Store(Path(d) / "db.sqlite3") as store:
                result = import_extractions(extractions, store, details)
                self.assertEqual(result["imported"], 1)
                self.assertEqual(len(store.list_jobs()), 1)


if __name__ == "__main__":
    unittest.main()
