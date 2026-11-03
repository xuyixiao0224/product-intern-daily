import tempfile
import unittest
from pathlib import Path

from product_intern_daily.cli import main


class InitTest(unittest.TestCase):
    def test_init_yes(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(["init", "--yes", "--dir", d]), 0)
            self.assertTrue((Path(d) / "run.sh").exists())
            self.assertIn("产品实习", (Path(d) / "run.sh").read_text(encoding="utf-8"))
            self.assertIn("RESEND_API_KEY", (Path(d) / ".env.example").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
