import unittest

from src.utils.player_profile import (
    parse_player_profile_sections,
    validate_player_profile_sections,
)


class TestPlayerProfileSections(unittest.TestCase):
    def test_parse_collapses_basic_info_into_single_card(self):
        sections = parse_player_profile_sections(
            {
                "format": "labelled_lines_v1",
                "detail": (
                    "生まれ::1999年2月25日、イタリア・カステッランマーレ・ディ・スタービア\n"
                    "国籍::イタリア\n"
                    "ポジション::ゴールキーパー\n"
                    "身長・利き足::196cm / 右足\n"
                    "特徴::反応速度とリーチに強み"
                ),
            }
        )

        self.assertEqual(
            sections,
            [
                {
                    "label": "基本情報",
                    "body": (
                        "生まれ：1999年2月25日、イタリア・カステッランマーレ・ディ・スタービア\n"
                        "国籍：イタリア\n"
                        "ポジション：ゴールキーパー\n"
                        "身長・利き足：196cm / 右足"
                    ),
                },
                {"label": "特徴", "body": "反応速度とリーチに強み"},
            ],
        )

    def test_parse_merges_unlabelled_lines_into_same_section(self):
        sections = parse_player_profile_sections(
            {
                "format": "labelled_lines_v1",
                "detail": (
                    "経歴::リヨン生まれ。7歳でアカデミー入り\n"
                    "2019-2025: オリンピック・リヨン（アカデミー→トップ）\n"
                    "2025-: マンチェスター・シティ"
                ),
            }
        )

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["label"], "経歴")
        self.assertEqual(
            sections[0]["body"],
            (
                "リヨン生まれ。7歳でアカデミー入り\n"
                "2019-2025: オリンピック・リヨン（アカデミー→トップ）\n"
                "2025-: マンチェスター・シティ"
            ),
        )

    def test_validate_rejects_multiple_history_cards(self):
        sections = [
            {"label": "経歴", "body": "アンジェ"},
            {"label": "経歴", "body": "ウルヴァーハンプトン"},
        ]

        with self.assertRaisesRegex(ValueError, "must stay in a single card.*経歴"):
            validate_player_profile_sections(
                sections, player_id="21138", player_name="R. Ait-Nouri"
            )


if __name__ == "__main__":
    unittest.main()
