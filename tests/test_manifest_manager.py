import json
import tempfile
import unittest
from pathlib import Path

from src.manifest_manager import (
    ManifestManager,
    dedupe_matches_by_fixture_id,
    prune_missing_manifest_entries,
)


class TestManifestManager(unittest.TestCase):
    def test_prune_missing_manifest_entries_removes_missing_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir)
            (reports_dir / "existing.html").write_text("ok", encoding="utf-8")
            manifest = {
                "reports_by_date": {
                    "2026-03-08": {
                        "matches": [
                            {"file": "existing.html", "fixture_id": 1},
                            {"file": "missing.html", "fixture_id": 2},
                        ]
                    },
                    "2026-03-09": {
                        "matches": [{"file": "missing-only.html", "fixture_id": 3}]
                    },
                }
            }

            pruned, removed_files = prune_missing_manifest_entries(
                manifest, reports_dir
            )

            self.assertEqual(removed_files, ["missing.html", "missing-only.html"])
            self.assertEqual(
                pruned["reports_by_date"]["2026-03-08"]["matches"],
                [{"file": "existing.html", "fixture_id": 1}],
            )
            self.assertNotIn("2026-03-09", pruned["reports_by_date"])

    def test_save_prunes_missing_entries_before_writing_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "existing.html").write_text("ok", encoding="utf-8")
            manifest_path = reports_dir / "manifest.json"

            manager = ManifestManager(manifest_path=manifest_path)
            manager._manifest = {
                "reports_by_date": {
                    "2026-03-08": {
                        "matches": [
                            {"file": "existing.html", "fixture_id": 1},
                            {"file": "missing.html", "fixture_id": 2},
                        ]
                    }
                }
            }

            manager.save()

            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["reports_by_date"]["2026-03-08"]["matches"],
                [{"file": "existing.html", "fixture_id": 1}],
            )

    def test_dedupe_matches_by_fixture_id_keeps_latest_in_same_date(self):
        manifest = {
            "reports_by_date": {
                "2026-02-28": {
                    "matches": [
                        {
                            "fixture_id": 1379244,
                            "file": "2026-02-28_Leeds_vs_ManchesterCity_20260307_161318.html",
                        },
                        {
                            "fixture_id": 1379244,
                            "file": "2026-02-28_Leeds_vs_ManchesterCity_20260307_182433.html",
                        },
                    ],
                },
            },
        }

        deduped, dropped = dedupe_matches_by_fixture_id(manifest)

        matches = deduped["reports_by_date"]["2026-02-28"]["matches"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0]["file"],
            "2026-02-28_Leeds_vs_ManchesterCity_20260307_182433.html",
        )
        self.assertEqual(
            dropped,
            ["2026-02-28_Leeds_vs_ManchesterCity_20260307_161318.html"],
        )

    def test_dedupe_matches_by_fixture_id_treats_string_and_int_equal(self):
        manifest = {
            "reports_by_date": {
                "2026-02-28": {
                    "matches": [
                        {
                            "fixture_id": "1379244",
                            "file": "match_20260307_161318.html",
                        },
                        {
                            "fixture_id": 1379244,
                            "file": "match_20260307_182433.html",
                        },
                    ],
                },
            },
        }

        deduped, dropped = dedupe_matches_by_fixture_id(manifest)

        matches = deduped["reports_by_date"]["2026-02-28"]["matches"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["file"], "match_20260307_182433.html")
        self.assertEqual(dropped, ["match_20260307_161318.html"])

    def test_dedupe_matches_by_fixture_id_drops_old_across_dates(self):
        manifest = {
            "reports_by_date": {
                "2026-02-27": {
                    "matches": [
                        {"fixture_id": 1, "file": "a_20260301_120000.html"},
                    ],
                },
                "2026-02-28": {
                    "matches": [
                        {"fixture_id": 1, "file": "a_20260302_090000.html"},
                    ],
                },
            },
        }

        deduped, dropped = dedupe_matches_by_fixture_id(manifest)

        self.assertNotIn("2026-02-27", deduped["reports_by_date"])
        self.assertEqual(
            deduped["reports_by_date"]["2026-02-28"]["matches"][0]["file"],
            "a_20260302_090000.html",
        )
        self.assertEqual(dropped, ["a_20260301_120000.html"])

    def test_dedupe_matches_by_fixture_id_preserves_unrelated_entries(self):
        manifest = {
            "reports_by_date": {
                "2026-02-28": {
                    "matches": [
                        {"fixture_id": 1, "file": "a_20260301_120000.html"},
                        {"fixture_id": 2, "file": "b_20260301_120000.html"},
                        {"file": "no_fixture_id.html"},
                    ],
                },
            },
        }

        deduped, dropped = dedupe_matches_by_fixture_id(manifest)

        matches = deduped["reports_by_date"]["2026-02-28"]["matches"]
        self.assertEqual(len(matches), 3)
        self.assertEqual(dropped, [])

    def test_save_dedupes_duplicate_fixture_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            old_file = "leeds_vs_mc_20260307_161318.html"
            new_file = "leeds_vs_mc_20260307_182433.html"
            (reports_dir / old_file).write_text("ok", encoding="utf-8")
            (reports_dir / new_file).write_text("ok", encoding="utf-8")
            manifest_path = reports_dir / "manifest.json"

            manager = ManifestManager(manifest_path=manifest_path)
            manager._manifest = {
                "reports_by_date": {
                    "2026-02-28": {
                        "matches": [
                            {"fixture_id": 1379244, "file": old_file},
                            {"fixture_id": 1379244, "file": new_file},
                        ],
                    },
                },
            }

            manager.save()

            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            matches = saved["reports_by_date"]["2026-02-28"]["matches"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["file"], new_file)


if __name__ == "__main__":
    unittest.main()
