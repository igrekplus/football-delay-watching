import unittest

from src.formatters.youtube_section_formatter import YouTubeSectionFormatter
from src.utils.api_stats import ApiStats


class TestDebugInfo(unittest.TestCase):
    def setUp(self):
        ApiStats.reset()

    def tearDown(self):
        ApiStats.reset()

    def test_debug_section_includes_fixture_id_and_shared_content(self):
        formatter = YouTubeSectionFormatter()

        html = formatter.format_debug_video_section(
            fixture_id="1379248",
            match_rank="S",
            shared_debug_html="<div>shared debug</div>",
        )

        self.assertIn("<summary>🛠️ デバッグ情報</summary>", html)
        self.assertIn("<strong>Fixture ID:</strong> 1379248", html)
        self.assertIn("<strong>Importance:</strong> S", html)
        self.assertIn("<div>shared debug</div>", html)
        self.assertNotIn("対象外動画一覧", html)

    def test_api_stats_uses_updated_console_urls(self):
        table = ApiStats.format_table()

        self.assertIn("https://console.cloud.google.com/billing?authuser=1", table)
        self.assertIn(
            "https://aistudio.google.com/app/u/1/api-keys?pli=1&project=gen-lang-client-0394252790",
            table,
        )

    def test_debug_section_hides_string_none_rank(self):
        formatter = YouTubeSectionFormatter()

        html = formatter.format_debug_video_section(
            fixture_id="1379248",
            match_rank="None",
        )

        self.assertIn("<strong>Fixture ID:</strong> 1379248", html)
        self.assertNotIn("Importance", html)


if __name__ == "__main__":
    unittest.main()
