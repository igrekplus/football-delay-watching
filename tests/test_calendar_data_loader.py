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

    def test_update_invalid_id_no_league(self):
        # 存在しないIDかつリーグ名指定なし → 失敗すべき
        success = update_report_link("non_existent_id", self.test_link)
        self.assertFalse(success)

    def test_update_new_fixture_with_league(self):
        # 存在しないIDだがリーグ名指定あり → 新規ファイル/エントリ作成
        new_fid = "9999999"
        test_league = "EPL"
        success = update_report_link(
            new_fid,
            self.test_link,
            league_name=test_league,
            match_data={
                "date_jst": "2026-02-08",
                "home_team": "TestHome",
                "away_team": "TestAway",
            },
        )
        self.assertTrue(success)

        info = get_calendar_info(new_fid)
        self.assertIsNotNone(info)
        self.assertEqual(info["report_link"], self.test_link)

        # クリーンアップ：テスト行を削除
        import csv
        import os

        from settings.calendar_data_loader import DATA_DIR

        path = os.path.join(DATA_DIR, "epl.csv")
        rows = []
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row.get("fixture_id") != new_fid:
                    rows.append(row)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        clear_cache()

    def test_dynamic_league_mapping(self):
        # Premier League -> EPL のマッピングが動的に行われるか確認
        # fixture_id 1379214 は EPL (Leeds vs Nottingham Forest)
        fid = "1379214"
        success = update_report_link(fid, self.test_link, league_name="Premier League")
        self.assertTrue(success)

        info = get_calendar_info(fid)
        self.assertEqual(info["report_link"], self.test_link)
        self.assertTrue(info["_source_file"].endswith("epl.csv"))


if __name__ == "__main__":
    unittest.main()
