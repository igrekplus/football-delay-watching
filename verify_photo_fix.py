import unittest

from src.formatters.matchup_formatter import MatchupFormatter
from src.parsers.former_club_parser import FormerClubEntry


class TestPhotoFix(unittest.TestCase):
    def test_extended_photos(self):
        formatter = MatchupFormatter()

        # 模擬データ
        eng_name = "Ferran Torres"
        jp_name = "フェラン・トーレス"
        photo_url = "https://example.com/ferran.png"

        # 通常の辞書（英語名のみ）
        player_photos = {eng_name: photo_url}

        # 拡張辞書（英語 + 日本語）
        player_photos_extended = {eng_name: photo_url, jp_name: photo_url}

        entry = FormerClubEntry(name=jp_name, team="FC Barcelona", description="Test")

        # 1. 英語名のみの場合（失敗するはず）
        html_fail = formatter.format_single_former_club(entry, player_photos, {})
        self.assertIn("matchup-photo-placeholder", html_fail)

        # 2. 拡張辞書の場合（成功するはず）
        html_success = formatter.format_single_former_club(
            entry, player_photos_extended, {}
        )
        self.assertIn(f'src="{photo_url}"', html_success)
        print("Verification successful: Extended photos allow matching Japanese names!")


if __name__ == "__main__":
    unittest.main()
