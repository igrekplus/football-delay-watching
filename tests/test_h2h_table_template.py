import unittest

from src.template_engine import render_template


class TestH2HTableTemplate(unittest.TestCase):
    def test_h2h_table_does_not_render_result_column(self):
        html = render_template(
            "partials/h2h_table.html",
            h2h_details=[
                {
                    "date": "2025-12-01",
                    "competition": "Premier League",
                    "league_logo": "",
                    "home": "Liverpool",
                    "home_logo": "",
                    "away": "Man City",
                    "away_logo": "",
                    "score": "2-1",
                    "winner": "Liverpool",
                    "result_key": "W",
                }
            ],
        )

        self.assertIn("<th>スコア</th>", html)
        self.assertNotIn("<th>結果</th>", html)
        self.assertNotIn("Win", html)
        self.assertNotIn("Draw", html)
        self.assertNotIn("Loss", html)


if __name__ == "__main__":
    unittest.main()
