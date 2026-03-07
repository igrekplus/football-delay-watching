import tempfile
import unittest
from pathlib import Path

from scripts import generate_player_profile_html


class TestGeneratePlayerProfileHtml(unittest.TestCase):
    def test_resolve_output_path_prefers_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            existing = output_dir / "156477-rayan-cherki.html"
            existing.write_text("", encoding="utf-8")

            resolved = generate_player_profile_html.resolve_output_path(
                player_id="156477",
                player_name="R. Cherki",
                output_path=None,
                output_dir=str(output_dir),
            )

            self.assertEqual(resolved, existing)

    def test_resolve_output_path_falls_back_to_slug(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)

            resolved = generate_player_profile_html.resolve_output_path(
                player_id="41621",
                player_name="Matheus Nunes",
                output_path=None,
                output_dir=str(output_dir),
            )

            self.assertEqual(resolved, output_dir / "41621-matheus-nunes.html")

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


if __name__ == "__main__":
    unittest.main()
