import unittest

from settings.calendar_data_loader import (
    clear_cache,
    get_calendar_info,
    load_all_calendar_data,
    update_report_link,
)


class TestCalendarDataLoader(unittest.TestCase):
    def setUp(self):
        clear_cache()
        # テスト用のデータを特定する（EPLの最初の項目など）
        self.fixture_id = "1379214"
        self.test_link = "/reports/test_report.html"

    def test_load_all_data(self):
        data = load_all_calendar_data()
        self.assertIn(self.fixture_id, data)
        item = data[self.fixture_id]
        self.assertIn("commentator", item)
        self.assertIn("report_link", item)

    def test_get_calendar_info(self):
        info = get_calendar_info(self.fixture_id)
        self.assertIsNotNone(info)
        self.assertEqual(info["commentator"], "坪井慶介")

    def test_update_report_link(self):
        # 準備：元に戻せるように現在の値を取得
        original_info = get_calendar_info(self.fixture_id)
        original_link = original_info.get("report_link", "")

        try:
            # 更新
            success = update_report_link(self.fixture_id, self.test_link)
            self.assertTrue(success)

            # 確認
            updated_info = get_calendar_info(self.fixture_id)
            self.assertEqual(updated_info["report_link"], self.test_link)

            # 別ファイルから読み直しても反映されているか
            clear_cache()
            updated_info_fresh = get_calendar_info(self.fixture_id)
            self.assertEqual(updated_info_fresh["report_link"], self.test_link)

        finally:
            # 後片付け：元の値に戻す
            update_report_link(self.fixture_id, original_link)


if __name__ == "__main__":
    unittest.main()
