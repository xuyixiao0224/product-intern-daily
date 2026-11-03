import json
import unittest

from product_intern_daily.mcp_client import MCPError, parse_search_response


class MCPClientTest(unittest.TestCase):
    def test_parse_search(self):
        text = json.dumps({"feeds": [
            {"id": "p1", "xsecToken": "t1", "noteCard": {"displayTitle": "AI产品实习", "user": {"nickname": "作者"}, "interactInfo": {"likedCount": "12", "commentCount": "3"}}},
            {"id": "p2", "xsecToken": "t2", "noteCard": {"displayTitle": "面经"}},
        ]}, ensure_ascii=False)
        rows = parse_search_response(text, keyword="AI产品实习", limit=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].post_id, "p1")
        self.assertEqual(rows[0].title, "AI产品实习")
        self.assertEqual(rows[0].likes, 12)
        self.assertEqual(rows[0].comments, 3)
        self.assertEqual(rows[1].author, "")

    def test_limit(self):
        text = json.dumps({"feeds": [{"id": f"p{i}", "xsecToken": "t"} for i in range(5)]})
        self.assertEqual(len(parse_search_response(text, limit=2)), 2)

    def test_bad_json(self):
        with self.assertRaises(MCPError):
            parse_search_response("not json")


if __name__ == "__main__":
    unittest.main()
