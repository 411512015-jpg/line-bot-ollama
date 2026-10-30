"""不需要 LINE token 或 Ollama 的基本測試。

執行：
    python -m unittest discover -s tests -v
"""

import unittest
from unittest.mock import patch

import relay_server


class QueryCleanupTests(unittest.TestCase):
    def test_strip_prefix_and_question_words(self):
        self.assertEqual(relay_server.clean_query("查 玉山有多高"), "玉山")
        self.assertEqual(relay_server.clean_query("查詢 台北車站在哪裡？"), "台北車站")

    def test_keep_meaningful_news_query(self):
        self.assertIn("台灣", relay_server.clean_query("查 今天台灣有什麼新聞"))


class SearchRoutingTests(unittest.TestCase):
    @patch("relay_server._search_wikipedia", return_value=[])
    @patch("relay_server._search_google_news", return_value=[])
    def test_news_query_hits_google_news_first(self, news, wiki):
        relay_server.search_web("查 今天有什麼新聞")
        self.assertTrue(news.called)
        self.assertTrue(wiki.called)
        self.assertEqual(news.call_args.kwargs["limit"], 3)

    @patch("relay_server._search_wikipedia", return_value=[])
    @patch("relay_server._search_google_news", return_value=[])
    def test_knowledge_query_hits_wikipedia_first(self, news, wiki):
        relay_server.search_web("查 玉山有多高")
        self.assertTrue(wiki.called)
        self.assertEqual(wiki.call_args.kwargs["limit"], 3)


class ExpenseTests(unittest.TestCase):
    def test_parse_expense_simple(self):
        exp = relay_server.parse_expense("咖啡 45 元")
        self.assertEqual(exp["merchant"], "咖啡")
        self.assertEqual(exp["amount"], 45.0)
        self.assertEqual(exp["category"], "飲食")

    def test_parse_expense_with_verb_and_merchant(self):
        exp = relay_server.parse_expense("買全聯 300 早餐")
        self.assertEqual(exp["merchant"], "全聯")
        self.assertEqual(exp["amount"], 300.0)
        self.assertEqual(exp["category"], "飲食")

    def test_parse_expense_without_amount_is_todo(self):
        self.assertIsNone(relay_server.parse_expense("買牛奶"))

    def test_expense_summary_today_month_and_category(self):
        from datetime import date

        today = date.today().strftime("%Y-%m-%d")
        fake = [
            {"time": today + " 10:00:00", "merchant": "咖啡", "amount": 45.0, "category": "飲食"},
            {"time": today + " 12:00:00", "merchant": "Uber", "amount": 60.0, "category": "交通"},
            {"time": "2000-01-01 09:00:00", "merchant": "舊筆", "amount": 10.0, "category": "其他"},
        ]
        with patch("relay_server.read_expenses", return_value=fake):
            s = relay_server.expense_summary()
        self.assertEqual(s["today"], 105.0)
        self.assertEqual(s["month"], 105.0)
        self.assertEqual(s["by_category"], {"飲食": 45.0, "交通": 60.0})
        self.assertEqual(s["last_month"], 0.0)
        self.assertEqual(s["last_month_by_category"], {})


class AnswerTests(unittest.TestCase):
    @patch("relay_server.ask_ollama", return_value="玉山主峰高 3,952 公尺。")
    @patch(
        "relay_server.search_web",
        return_value=[
            {"title": "玉山（維基百科）", "url": "https://zh.wikipedia.org/wiki/玉山", "snippet": ""},
        ],
    )
    def test_answer_includes_sources(self, search, ollama):
        answer = relay_server.build_answer("查 玉山有多高")
        self.assertIn("3,952", answer)
        self.assertIn("來源：", answer)
        self.assertIn("zh.wikipedia.org", answer)
        ollama.assert_called_once()

    @patch("relay_server.ask_ollama", return_value="找不到資料。")
    @patch("relay_server.search_web", return_value=[])
    def test_answer_without_sources_is_ok(self, search, ollama):
        answer = relay_server.build_answer("查 冷門問題")
        self.assertEqual(answer, "找不到資料。")
        self.assertNotIn("來源：", answer)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.client = relay_server.app.test_client()

    def test_health_does_not_expose_secrets(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertNotIn("token", str(body).lower())

    @patch("relay_server.build_answer", return_value="測試答案\n\n來源：\n1. 範例\n   https://example.com")
    def test_ask_without_reply_token_returns_json(self, build):
        res = self.client.post("/ask", json={"question": "查 測試"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("測試答案", res.get_json()["answer"])

    @patch("relay_server.build_answer", return_value="展示答案")
    def test_demo_answer_mode(self, build):
        res = self.client.post("/demo/message", json={"text": "查 玉山"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["kind"], "answer")

    @patch("relay_server.append_todo")
    def test_demo_todo_mode(self, append):
        res = self.client.post("/demo/message", json={"text": "買牛奶"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["kind"], "todo")
        append.assert_called_once_with("買牛奶")

    @patch("relay_server.expense_summary", return_value={"today": 45.0, "month": 45.0, "by_category": {"飲食": 45.0}})
    @patch("relay_server.append_expense")
    def test_demo_expense_mode(self, append, summary):
        res = self.client.post("/demo/message", json={"text": "咖啡 45 元"})
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["kind"], "expense")
        self.assertEqual(body["merchant"], "咖啡")
        self.assertEqual(body["category"], "飲食")
        self.assertIn("累計", body["reply"])
        append.assert_called_once()

    def test_demo_expenses_endpoint_lists_expenses(self):
        with patch("relay_server.read_expenses", return_value=[]):
            res = self.client.get("/demo/expenses")
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body["expenses"], [])
        self.assertIn("summary", body)

    def test_empty_message_is_rejected(self):
        res = self.client.post("/demo/message", json={"text": "   "})
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
