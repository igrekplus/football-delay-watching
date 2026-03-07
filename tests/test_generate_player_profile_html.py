import tempfile
import unittest
from pathlib import Path

from scripts import generate_player_profile_html


class TestGeneratePlayerProfileHtml(unittest.TestCase):
    def test_resolve_output_path_uses_player_id_stable_filename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            resolved = generate_player_profile_html.resolve_output_path(
                player_id="156477",
                player_name="R. Cherki",
                output_path=None,
                output_dir=str(output_dir),
            )

            self.assertEqual(resolved, output_dir / "156477.html")

    def test_resolve_output_path_falls_back_to_player_id_filename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            resolved = generate_player_profile_html.resolve_output_path(
                player_id="41621",
                player_name="Matheus Nunes",
                output_path=None,
                output_dir=str(output_dir),
            )

            self.assertEqual(resolved, output_dir / "41621.html")

    def test_resolve_output_path_uses_project_root_for_relative_override(self):
        resolved = generate_player_profile_html.resolve_output_path(
            player_id="41621",
            player_name="Matheus Nunes",
            output_path="custom/player-profile.html",
            output_dir="public/player-profiles",
        )

        self.assertEqual(
            resolved,
            generate_player_profile_html.PROJECT_ROOT
            / "custom"
            / "player-profile.html",
        )

    def test_render_profile_html_rejects_split_history_cards(self):
        row = {
            "player_id": "21138",
            "name": "R. Aït-Nouri",
            "profile_format": "labelled_lines_v1",
            "profile_detail": "経歴::アンジェ\\n経歴::ウルヴァーハンプトン",
        }

        with self.assertRaisesRegex(ValueError, "must stay in a single card.*経歴"):
            generate_player_profile_html.render_profile_html(row)

    def test_render_profile_html_groups_basic_info_card(self):
        row = {
            "player_id": "1622",
            "name": "G. Donnarumma",
            "profile_format": "labelled_lines_v1",
            "profile_detail": (
                "生まれ::1999年2月25日、イタリア・カステッランマーレ・ディ・スタービア\\n"
                "国籍::イタリア\\n"
                "ポジション::ゴールキーパー\\n"
                "身長・利き足::196cm / 右足\\n"
                "特徴::至近距離への反応に強い"
            ),
        }

        html = generate_player_profile_html.render_profile_html(row)

        self.assertIn("<h4>基本情報</h4>", html)
        self.assertIn(
            "生まれ：1999年2月25日、イタリア・カステッランマーレ・ディ・スタービア",
            html,
        )
        self.assertIn("国籍：イタリア", html)
        self.assertIn("<h4>特徴</h4>", html)


if __name__ == "__main__":
    unittest.main()
