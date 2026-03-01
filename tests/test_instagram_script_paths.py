import unittest
from pathlib import Path

from scripts import analyze_missing_instagram, fetch_squad_list


class TestInstagramScriptPaths(unittest.TestCase):
    def test_analyze_missing_instagram_resolves_default_from_project_root(self):
        csv_path = analyze_missing_instagram.resolve_csv_path(50, None)

        self.assertEqual(
            csv_path,
            analyze_missing_instagram.PROJECT_ROOT / "data" / "player_50.csv",
        )

    def test_analyze_missing_instagram_resolves_relative_override_from_project_root(
        self,
    ):
        csv_path = analyze_missing_instagram.resolve_csv_path(50, "custom/output.csv")

        self.assertEqual(
            csv_path,
            analyze_missing_instagram.PROJECT_ROOT / "custom" / "output.csv",
        )

    def test_fetch_squad_list_resolves_default_output_from_project_root(self):
        output_path = fetch_squad_list.resolve_output_path(42, None)

        self.assertEqual(
            output_path,
            fetch_squad_list.PROJECT_ROOT / "data" / "player_42.csv",
        )

    def test_fetch_squad_list_keeps_absolute_override(self):
        absolute_path = Path("/tmp/player_test.csv")

        self.assertEqual(
            fetch_squad_list.resolve_output_path(42, str(absolute_path)),
            absolute_path,
        )


if __name__ == "__main__":
    unittest.main()
