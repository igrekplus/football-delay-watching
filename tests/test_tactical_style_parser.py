import unittest

from src.parsers.tactical_style_parser import parse_tactical_style_text


class TestTacticalStyleParser(unittest.TestCase):
    def test_parse_colon_format(self):
        text = """
### 🎯 戦術スタイル
Barcelona:
バルセロナは伝統的なポゼッションサッカーを重視しつつも、近年はよりダイレクトな攻撃を織り交ぜたハイブリッドな戦術を採用しています.

Mallorca:
マジョルカは、堅守速攻をベースとした戦術を採用しています.
"""
        home_team = "Barcelona"
        away_team = "Mallorca"

        results = parse_tactical_style_text(text, home_team, away_team)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].team, "Barcelona")
        self.assertTrue(results[0].description.startswith("バルセロナは"))
        self.assertEqual(results[1].team, "Mallorca")
        self.assertTrue(results[1].description.startswith("マジョルカは"))

    def test_parse_structured_format(self):
        text = """
#### Barcelona
ポゼッション重視のスタイル。

#### Mallorca
堅守速攻のスタイル。
"""
        home_team = "Barcelona"
        away_team = "Mallorca"

        results = parse_tactical_style_text(text, home_team, away_team)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].team, "Barcelona")
        self.assertEqual(results[1].team, "Mallorca")

    def test_parse_paragraph_format(self):
        text = """
Barcelonaは伝統的な...
Mallorcaは堅守速攻...
"""
        home_team = "Barcelona"
        away_team = "Mallorca"

        results = parse_tactical_style_text(text, home_team, away_team)

        self.assertEqual(len(results), 2)  # 修正後: 空行がなくてもパース可能

    def test_parse_paragraph_format_with_newline(self):
        text = """
Barcelonaは伝統的な...

Mallorcaは堅守速攻...
"""
        home_team = "Barcelona"
        away_team = "Mallorca"

        results = parse_tactical_style_text(text, home_team, away_team)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].team, "Barcelona")
        self.assertEqual(results[1].team, "Mallorca")

    def test_parse_complex_names_and_no_newlines(self):
        # 修正後のより柔軟なテスト
        text = """
Real Betis: ベティスの戦術...
Atletico Madrid: アトレティコの戦術...
"""
        home_team = "Real Betis"
        away_team = "Atletico Madrid"

        results = parse_tactical_style_text(text, home_team, away_team)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].team, "Real Betis")
        self.assertTrue("ベティスの戦術" in results[0].description)
        self.assertEqual(results[1].team, "Atletico Madrid")
        self.assertTrue("アトレティコの戦術" in results[1].description)

    def test_parse_bold_markdown_with_symbols(self):
        # 現実の LLM 出力に近いパターン
        text = """
**Liverpool:** リヴァプールは、...
**Manchester City:** マンチェスター・シティは、...
"""
        home_team = "Liverpool"
        away_team = "Manchester City"

        results = parse_tactical_style_text(text, home_team, away_team)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].team, "Liverpool")
        self.assertEqual(results[1].team, "Manchester City")
        # 記号が除去されていること
        self.assertFalse(results[0].description.startswith("*"))
        self.assertFalse(results[0].description.startswith(":"))
        self.assertTrue(results[0].description.startswith("リヴァプールは"))


if __name__ == "__main__":
    unittest.main()
