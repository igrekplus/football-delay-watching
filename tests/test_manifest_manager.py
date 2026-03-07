import json
import tempfile
import unittest
from pathlib import Path

from src.manifest_manager import ManifestManager, prune_missing_manifest_entries


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


if __name__ == "__main__":
    unittest.main()
