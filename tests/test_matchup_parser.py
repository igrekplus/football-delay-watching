"""MatchupParserのユニットテスト (unittest版)"""
import unittest
from src.parsers.matchup_parser import parse_matchup_text

class TestMatchupParser(unittest.TestCase):
    def test_parse_simple_matchup(self):
        text = """
🇯🇵 **日本**
**三笘薫**（ブライトン）と**冨安健洋**（アーセナル）。プレミアリーグで活躍する日本代表の主力二人の対戦は大きな注目を集める。
"""
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].header, "🇯🇵 日本")
        self.assertEqual(len(result[0].players), 2)
        self.assertEqual(result[0].players[0][0], "三笘薫")
        self.assertEqual(result[0].players[0][1], "ブライトン")
        self.assertEqual(result[0].players[1][0], "冨安健洋")
        self.assertEqual(result[0].players[1][1], "アーセナル")
        self.assertIn("注目を集める", result[0].description)

    def test_parse_vs_matchup(self):
        text = """
1. **エース対決**
**ハーランド**（Man City） vs **サラー**（Liverpool）。得点王を争う二人の直接対決。
"""
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        # 2番目のフォールバックパターンでマッチした場合はヘッダーが空になる仕様を確認
        self.assertEqual(result[0].header, "")
        self.assertEqual(len(result[0].players), 2)
        self.assertEqual(result[0].players[0][0], "ハーランド")
        self.assertEqual(result[0].players[0][1], "Man City")
        self.assertEqual(result[0].players[1][0], "サラー")
        self.assertEqual(result[0].players[1][1], "Liverpool")
        self.assertIn("得点王を争う", result[0].description)

    def test_parse_multiple_matchups(self):
        text = """
🏴󠁧󠁢󠁳󠁣󠁴󠁿 **スコットランド**
**アンディ・ロバートソン**（リヴァプール）と**スコット・マクトミネイ**（マンチェスター・ユナイテッド）。代表の主将と中盤の要。

🏴󠁧󠁢󠁥󠁮󠁧󠁿 **イングランド**
**ハリー・ケイン**（バイエルン）と**ジュード・ベリンガム**（レアル・マドリード）。三冠を狙うエース同士。
"""
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].header, "🏴󠁧󠁢󠁳󠁣󠁴󠁿 スコットランド")
        self.assertEqual(result[1].header, "🏴󠁧󠁢󠁥󠁮󠁧󠁿 イングランド")

    def test_parse_4_players_matchup(self):
        """最大4名対応のテスト"""
        text = """
🇧🇷 **Brazil**
**Joelinton** (Newcastle)、**Bruno Guimarães** (Newcastle)と**Ederson** (Manchester City)、**Matheus Nunes** (Manchester City)。両チームにブラジル人選手が多数在籍。
"""
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].header, "🇧🇷 Brazil")
        self.assertEqual(len(result[0].players), 4)
        self.assertEqual(result[0].players[0], ("Joelinton", "Newcastle"))
        self.assertEqual(result[0].players[1], ("Bruno Guimarães", "Newcastle"))
        self.assertEqual(result[0].players[2], ("Ederson", "Manchester City"))
        self.assertEqual(result[0].players[3], ("Matheus Nunes", "Manchester City"))
        self.assertIn("多数在籍", result[0].description)

    def test_parse_half_width_parentheses(self):
        text = """
🇯🇵 **日本**
**三笘薫**(ブライトン)と**冨安健洋**(アーセナル)。半角括弧のテスト。
"""
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].players[0][1], "ブライトン")
        self.assertEqual(result[0].players[1][1], "アーセナル")

    def test_parse_empty_input(self):
        self.assertEqual(parse_matchup_text(""), [])
        self.assertEqual(parse_matchup_text(None), [])

    def test_parse_invalid_format(self):
        text = "普通のテキスト。パースできないはず。"
        self.assertEqual(parse_matchup_text(text), [])

    def test_parse_xss_protection(self):
        text = """
        1. **<script>alert('xss')</script>**
        **選手A**（<img src=x onerror=alert(1)>）と**選手B**（チームB）。説明。
        """
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        # 1.パターンの場合もヘッダー抽出ロジックによってヘッダーが空になるか、
        # または_process_sectionで処理されるかによるが、
        # 現状のコードでは '1. **...' は header_line_pattern にマッチしない（国旗が必要）
        # なので vs_pattern 側で処理され header は空になる
        self.assertEqual(result[0].header, "")
        self.assertIn("&lt;img", result[0].players[0][1])

    def test_parse_multiple_sentences_description(self):
        text = """
        🇯🇵 **日本**
        **三笘薫**（ブライトン）と**冨安健洋**（アーセナル）。一行目。二行目。三行目。
        """
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].description, "一行目。二行目。三行目。")

    def test_parse_complex_team_name(self):
        # チーム名に英数字や記号が含まれる場合
        text = """
        🇯🇵 **日本**
        **選手A**（FC Tokyo U-23）と**選手B**（1. FC Köln）。テスト。
        """
        result = parse_matchup_text(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].players[0][1], "FC Tokyo U-23")
        self.assertEqual(result[0].players[1][1], "1. FC Köln")

if __name__ == '__main__':
    unittest.main()
