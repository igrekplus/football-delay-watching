import csv
import os
import shutil
import tempfile
import unittest

from settings import calendar_data_loader as cdl


class TestCalendarDataLoader(unittest.TestCase):
    def setUp(self):
        self.fixture_id = "1379214"
        self.test_link = "/reports/test_report.html"

        self.temp_dir = tempfile.mkdtemp(prefix="calendar_data_loader_test_")
        self.original_data_dir = cdl.DATA_DIR
        self.original_use_gcs = cdl.USE_GCS_CALENDAR_STATUS

        cdl.DATA_DIR = self.temp_dir
        cdl.USE_GCS_CALENDAR_STATUS = False

        epl_path = os.path.join(self.temp_dir, "epl.csv")
        with open(epl_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cdl.CSV_COLUMNS)
            writer.writeheader()
            writer.writerow(
                {
                    "fixture_id": self.fixture_id,
                    "date_jst": "2026-02-07",
                    "home_team": "Leeds",
                    "away_team": "Nottingham Forest",
                    "commentator": "坪井慶介",
                    "announcer": "安井成行",
                    "report_link": "",
                }
            )

        cdl.clear_cache()

    def tearDown(self):
        cdl.DATA_DIR = self.original_data_dir
        cdl.USE_GCS_CALENDAR_STATUS = self.original_use_gcs
        cdl.clear_cache()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_all_data(self):
        data = cdl.load_all_calendar_data()
        self.assertIn(self.fixture_id, data)
        item = data[self.fixture_id]
        self.assertIn("commentator", item)
        self.assertIn("report_link", item)

    def test_get_calendar_info(self):
        info = cdl.get_calendar_info(self.fixture_id)
        self.assertIsNotNone(info)
        self.assertEqual(info["commentator"], "坪井慶介")

    def test_update_report_link(self):
        success = cdl.update_report_link(self.fixture_id, self.test_link)
        self.assertTrue(success)

        updated_info = cdl.get_calendar_info(self.fixture_id)
        self.assertEqual(updated_info["report_link"], self.test_link)

        cdl.clear_cache()
        updated_info_fresh = cdl.get_calendar_info(self.fixture_id)
        self.assertEqual(updated_info_fresh["report_link"], self.test_link)

    def test_update_invalid_id_no_league(self):
        success = cdl.update_report_link("non_existent_id", self.test_link)
        self.assertFalse(success)

    def test_update_new_fixture_with_league(self):
        new_fid = "9999999"
        success = cdl.update_report_link(
            new_fid,
            self.test_link,
            league_name="EPL",
            match_data={
                "date_jst": "2026-02-08",
                "home_team": "TestHome",
                "away_team": "TestAway",
            },
        )
        self.assertTrue(success)

        info = cdl.get_calendar_info(new_fid)
        self.assertIsNotNone(info)
        self.assertEqual(info["report_link"], self.test_link)
        self.assertTrue(info["_source_file"].endswith("epl.csv"))

    def test_dynamic_league_mapping(self):
        success = cdl.update_report_link(
            self.fixture_id, self.test_link, league_name="Premier League"
        )
        self.assertTrue(success)

        info = cdl.get_calendar_info(self.fixture_id)
        self.assertEqual(info["report_link"], self.test_link)
        self.assertTrue(info["_source_file"].endswith("epl.csv"))


if __name__ == "__main__":
    unittest.main()
