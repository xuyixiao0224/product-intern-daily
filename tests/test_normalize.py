import unittest
from product_intern_daily.normalize import extract_emails, make_dedup_key, normalize_emails


class NormalizeTest(unittest.TestCase):
    def test_extract_emails_dedup_and_lower(self):
        self.assertEqual(extract_emails("A@B.com; a@b.com, x@y.cn"), ["a@b.com", "x@y.cn"])

    def test_repair_ocr_email(self):
        self.assertEqual(extract_emails("简历发 example.user.gmail.com"), ["example.user@gmail.com"])
        self.assertEqual(extract_emails("foo(at)bar.com"), ["foo@bar.com"])

    def test_normalize_emails_list(self):
        self.assertEqual(normalize_emails(["HR@X.com", "hr@x.com"]), "hr@x.com")

    def test_dedup_email_first(self):
        self.assertEqual(make_dedup_key("HR@X.com", "字节", "产品", "p1"), "email:hr@x.com")

    def test_dedup_role_fallback(self):
        self.assertEqual(make_dedup_key("", "字节跳动", "AI 产品实习", "p1"), "role:字节跳动|ai产品实习")

    def test_dedup_note_fallback(self):
        self.assertEqual(make_dedup_key("", "", "", "p1"), "note:p1")


if __name__ == "__main__":
    unittest.main()
