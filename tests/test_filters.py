import unittest
from product_intern_daily.filters import buy_flags, closed_flags, is_aggregator_profile, is_help_seeking, referral_code


class FiltersTest(unittest.TestCase):
    def test_help_seeking(self):
        text = "收到了该岗位终面，请问大家这个岗位怎么样，未来职业发展想做pm/pmo的话，这是一个比较好的发展方向吗，有没有同岗的小伙伴分享一下捏"
        self.assertTrue(is_help_seeking(text))

    def test_buy_comment(self):
        self.assertIn("购买", buy_flags("购买笔记同款表格"))
        self.assertIn("同款表格", buy_flags("购买笔记同款表格"))

    def test_closed(self):
        self.assertIn("先不投", closed_flags("二编：目前简历已经筛完进入下一轮 大家可以先不投啦"))

    def test_aggregator_profile(self):
        self.assertTrue(is_aggregator_profile("每天更新岗位表，购买后进群", ["A公司", "B公司", "C公司"]))
        self.assertFalse(is_aggregator_profile("AI产品 PM 实习中｜实习分享", ["A公司", "B公司", "C公司"]))

    def test_referral(self):
        self.assertEqual(referral_code("内推码：campusurihXYHHd"), "campusurihXYHHd")


if __name__ == "__main__":
    unittest.main()
