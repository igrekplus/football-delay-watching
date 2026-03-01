import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import settings.player_instagram as player_instagram


class TestPlayerInstagram(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.csv_path = self.data_dir / "player_999.csv"
        self._write_rows(
            [
                [
                    1100,
                    "Erling Haaland",
                    "Attacker",
                    9,
                    "https://www.instagram.com/erling/",
                ],
                [
                    1422,
                    "J. Doku",
                    "Attacker",
                    11,
                    "https://www.instagram.com/jeremydoku/",
                ],
                [81573, "Omar Marmoush", "Attacker", 7, ""],
            ]
        )

        self.data_dir_patcher = mock.patch.object(
            player_instagram, "DATA_DIR", str(self.data_dir)
        )
        self.team_files_patcher = mock.patch.object(
            player_instagram, "TEAM_CSV_FILES", {999: "player_999.csv"}
        )
        self.use_gcs_patcher = mock.patch.object(
            player_instagram, "USE_GCS_PLAYER_DATA", False
        )
        self.data_dir_patcher.start()
        self.team_files_patcher.start()
        self.use_gcs_patcher.start()
        player_instagram.clear_cache()

    def tearDown(self):
        player_instagram.clear_cache()
        self.use_gcs_patcher.stop()
        self.team_files_patcher.stop()
        self.data_dir_patcher.stop()
        self.temp_dir.cleanup()

    def _write_rows(self, rows: list[list]):
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["player_id", "name", "position", "number", "instagram_url"]
            )
            writer.writerows(rows)

    def test_loads_instagram_urls_by_player_id(self):
        self.assertEqual(
            player_instagram.get_player_instagram_urls(),
            {
                1100: "https://www.instagram.com/erling/",
                1422: "https://www.instagram.com/jeremydoku/",
            },
        )
        self.assertEqual(
            player_instagram.get_player_instagram_urls_by_name(),
            {
                "Erling Haaland": "https://www.instagram.com/erling/",
                "J. Doku": "https://www.instagram.com/jeremydoku/",
            },
        )

    def test_get_instagram_url_accepts_int_and_string_player_ids(self):
        self.assertEqual(
            player_instagram.get_instagram_url(1100),
            "https://www.instagram.com/erling/",
        )
        self.assertEqual(
            player_instagram.get_instagram_url("1422"),
            "https://www.instagram.com/jeremydoku/",
        )
        self.assertIsNone(player_instagram.get_instagram_url(""))

    def test_clear_cache_reloads_updated_csv(self):
        self.assertEqual(
            player_instagram.get_instagram_url(1100),
            "https://www.instagram.com/erling/",
        )

        self._write_rows(
            [
                [
                    1100,
                    "Erling Haaland",
                    "Attacker",
                    9,
                    "https://www.instagram.com/erling_updated/",
                ]
            ]
        )

        self.assertEqual(
            player_instagram.get_instagram_url(1100),
            "https://www.instagram.com/erling/",
        )

        player_instagram.clear_cache()

        self.assertEqual(
            player_instagram.get_instagram_url(1100),
            "https://www.instagram.com/erling_updated/",
        )

    def test_prefers_gcs_csv_when_enabled(self):
        gcs_rows = [
            {
                "player_id": "1100",
                "name": "Erling Haaland",
                "position": "Attacker",
                "number": "9",
                "instagram_url": "https://www.instagram.com/erling_gcs/",
            }
        ]

        with mock.patch.object(player_instagram, "USE_GCS_PLAYER_DATA", True):
            with mock.patch.object(
                player_instagram,
                "_load_gcs_csv",
                return_value=player_instagram._rows_to_url_maps(
                    gcs_rows, "gcs://test/player_999.csv"
                ),
            ) as gcs_loader:
                player_instagram.clear_cache()
                self.assertEqual(
                    player_instagram.get_instagram_url(1100),
                    "https://www.instagram.com/erling_gcs/",
                )
                gcs_loader.assert_called_once_with("player_999.csv")

    def test_falls_back_to_local_csv_when_gcs_is_unavailable(self):
        with mock.patch.object(player_instagram, "USE_GCS_PLAYER_DATA", True):
            with mock.patch.object(
                player_instagram, "_load_gcs_csv", return_value=None
            ) as gcs_loader:
                player_instagram.clear_cache()
                self.assertEqual(
                    player_instagram.get_instagram_url(1100),
                    "https://www.instagram.com/erling/",
                )
                gcs_loader.assert_called_once_with("player_999.csv")


if __name__ == "__main__":
    unittest.main()
