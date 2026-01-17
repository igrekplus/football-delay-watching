"""
DateTimeUtil ユニットテスト

Issue #70: 日時/タイムゾーン処理の一元化
Issue #103: DRY: JST/日時処理の共通化
"""

import unittest
from datetime import datetime

try:
    from freezegun import freeze_time
except ImportError:
    freeze_time = None


from src.utils.datetime_util import JST, UTC, DateTimeUtil


class TestDateTimeUtil(unittest.TestCase):
    def test_parse_with_weekday(self):
        """曜日ありフォーマット: "2025/12/27(土) 21:30 JST" """
        result = DateTimeUtil.parse_kickoff_jst("2025/12/27(土) 21:30 JST")

        self.assertIsNotNone(result)
        self.assertEqual(result.tzinfo, UTC)
        # JST 21:30 = UTC 12:30
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 27)
        self.assertEqual(result.hour, 12)
        self.assertEqual(result.minute, 30)

    def test_parse_without_weekday(self):
        """曜日なしフォーマット: "2025/12/21 00:00 JST" """
        result = DateTimeUtil.parse_kickoff_jst("2025/12/21 00:00 JST")

        self.assertIsNotNone(result)
        self.assertEqual(result.tzinfo, UTC)
        # JST 00:00 = UTC 15:00 (前日)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 20)
        self.assertEqual(result.hour, 15)
        self.assertEqual(result.minute, 0)

    def test_parse_empty_string(self):
        """空文字列の場合はNoneを返す"""
        result = DateTimeUtil.parse_kickoff_jst("")
        self.assertIsNone(result)

    def test_parse_none(self):
        """Noneの場合はNoneを返す"""
        result = DateTimeUtil.parse_kickoff_jst(None)
        self.assertIsNone(result)

    def test_parse_invalid_format(self):
        """不正なフォーマットの場合はNoneを返す"""
        result = DateTimeUtil.parse_kickoff_jst("invalid format")
        self.assertIsNone(result)

    def test_jst_to_utc(self):
        """JST -> UTC 変換"""
        jst_dt = JST.localize(datetime(2025, 12, 27, 21, 30))
        result = DateTimeUtil.to_utc(jst_dt)

        self.assertEqual(result.tzinfo, UTC)
        self.assertEqual(result.hour, 12)  # 21:30 JST = 12:30 UTC
        self.assertEqual(result.minute, 30)

    def test_naive_to_utc(self):
        """naiveな datetime は JST として扱う"""
        naive_dt = datetime(2025, 12, 27, 21, 30)
        result = DateTimeUtil.to_utc(naive_dt)

        self.assertEqual(result.tzinfo, UTC)
        self.assertEqual(result.hour, 12)  # 21:30 JST = 12:30 UTC

    def test_utc_to_jst(self):
        """UTC -> JST 変換"""
        utc_dt = UTC.localize(datetime(2025, 12, 27, 12, 30))
        result = DateTimeUtil.to_jst(utc_dt)

        self.assertEqual(str(result.tzinfo), str(JST))
        self.assertEqual(result.hour, 21)  # 12:30 UTC = 21:30 JST
        self.assertEqual(result.minute, 30)

    def test_naive_to_jst(self):
        """naiveな datetime は UTC として扱う"""
        naive_dt = datetime(2025, 12, 27, 12, 30)
        result = DateTimeUtil.to_jst(naive_dt)

        self.assertEqual(str(result.tzinfo), str(JST))
        self.assertEqual(result.hour, 21)  # 12:30 UTC = 21:30 JST

    def test_format_with_weekday(self):
        """曜日あり表示"""
        utc_dt = UTC.localize(datetime(2025, 12, 27, 12, 30))
        result = DateTimeUtil.format_jst_display(utc_dt, include_weekday=True)

        self.assertEqual(result, "2025/12/27(土) 21:30 JST")

    def test_format_without_weekday(self):
        """曜日なし表示"""
        utc_dt = UTC.localize(datetime(2025, 12, 27, 12, 30))
        result = DateTimeUtil.format_jst_display(utc_dt, include_weekday=False)

        self.assertEqual(result, "2025/12/27 21:30 JST")

    def test_format_iso(self):
        """ISO 8601形式"""
        jst_dt = JST.localize(datetime(2025, 12, 27, 21, 30))
        result = DateTimeUtil.format_utc_iso(jst_dt)

        self.assertEqual(result, "2025-12-27T12:30:00Z")

    def test_format_report_datetime_arg(self):
        """指定時刻のレポート日時フォーマット"""
        dt = JST.localize(datetime(2025, 1, 1, 10, 0, 0))
        result = DateTimeUtil.format_report_datetime(dt)
        self.assertEqual(result, "2025-01-01_100000")

    def test_format_time_only_arg(self):
        """指定時刻の時刻のみフォーマット"""
        dt = JST.localize(datetime(2025, 1, 1, 10, 5, 30))
        result = DateTimeUtil.format_time_only(dt)
        self.assertEqual(result, "10:05:30")

    # freezegun がある場合のみ実行
    if freeze_time:

        @freeze_time("2025-12-27 21:30:00", tz_offset=9)
        def test_format_report_datetime_now(self):
            """現在時刻のレポート日時フォーマット (YYYY-MM-DD_HHMMSS)"""
            result = DateTimeUtil.format_report_datetime()
            self.assertEqual(result, "2025-12-27_213000")

        @freeze_time("2025-12-27 21:30:00", tz_offset=9)
        def test_format_time_only_now(self):
            """現在時刻の時刻のみフォーマット (HH:MM:S)"""
            result = DateTimeUtil.format_time_only()
            self.assertEqual(result, "21:30:00")
    else:
        print("Skipping freeze_time tests (freezegun not installed)")


if __name__ == "__main__":
    unittest.main()
