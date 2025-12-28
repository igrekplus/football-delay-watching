"""
DateTimeUtil ユニットテスト

Issue #70: 日時/タイムゾーン処理の一元化
"""

import pytest
from datetime import datetime
import pytz

from src.utils.datetime_util import DateTimeUtil, JST, UTC


class TestParseKickoffJst:
    """parse_kickoff_jst のテスト"""
    
    def test_parse_with_weekday(self):
        """曜日ありフォーマット: "2025/12/27(土) 21:30 JST" """
        result = DateTimeUtil.parse_kickoff_jst("2025/12/27(土) 21:30 JST")
        
        assert result is not None
        assert result.tzinfo == UTC
        # JST 21:30 = UTC 12:30
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 27
        assert result.hour == 12
        assert result.minute == 30
    
    def test_parse_without_weekday(self):
        """曜日なしフォーマット: "2025/12/21 00:00 JST" """
        result = DateTimeUtil.parse_kickoff_jst("2025/12/21 00:00 JST")
        
        assert result is not None
        assert result.tzinfo == UTC
        # JST 00:00 = UTC 15:00 (前日)
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 20
        assert result.hour == 15
        assert result.minute == 0
    
    def test_parse_empty_string(self):
        """空文字列の場合はNoneを返す"""
        result = DateTimeUtil.parse_kickoff_jst("")
        assert result is None
    
    def test_parse_none(self):
        """Noneの場合はNoneを返す"""
        result = DateTimeUtil.parse_kickoff_jst(None)
        assert result is None
    
    def test_parse_invalid_format(self):
        """不正なフォーマットの場合はNoneを返す"""
        result = DateTimeUtil.parse_kickoff_jst("invalid format")
        assert result is None


class TestToUtc:
    """to_utc のテスト"""
    
    def test_jst_to_utc(self):
        """JST -> UTC 変換"""
        jst_dt = JST.localize(datetime(2025, 12, 27, 21, 30))
        result = DateTimeUtil.to_utc(jst_dt)
        
        assert result.tzinfo == UTC
        assert result.hour == 12  # 21:30 JST = 12:30 UTC
        assert result.minute == 30
    
    def test_naive_to_utc(self):
        """naiveな datetime は JST として扱う"""
        naive_dt = datetime(2025, 12, 27, 21, 30)
        result = DateTimeUtil.to_utc(naive_dt)
        
        assert result.tzinfo == UTC
        assert result.hour == 12  # 21:30 JST = 12:30 UTC


class TestToJst:
    """to_jst のテスト"""
    
    def test_utc_to_jst(self):
        """UTC -> JST 変換"""
        utc_dt = UTC.localize(datetime(2025, 12, 27, 12, 30))
        result = DateTimeUtil.to_jst(utc_dt)
        
        assert result.tzinfo == JST
        assert result.hour == 21  # 12:30 UTC = 21:30 JST
        assert result.minute == 30
    
    def test_naive_to_jst(self):
        """naiveな datetime は UTC として扱う"""
        naive_dt = datetime(2025, 12, 27, 12, 30)
        result = DateTimeUtil.to_jst(naive_dt)
        
        assert result.tzinfo == JST
        assert result.hour == 21  # 12:30 UTC = 21:30 JST


class TestFormatJstDisplay:
    """format_jst_display のテスト"""
    
    def test_format_with_weekday(self):
        """曜日あり表示"""
        utc_dt = UTC.localize(datetime(2025, 12, 27, 12, 30))
        result = DateTimeUtil.format_jst_display(utc_dt, include_weekday=True)
        
        assert result == "2025/12/27(土) 21:30 JST"
    
    def test_format_without_weekday(self):
        """曜日なし表示"""
        utc_dt = UTC.localize(datetime(2025, 12, 27, 12, 30))
        result = DateTimeUtil.format_jst_display(utc_dt, include_weekday=False)
        
        assert result == "2025/12/27 21:30 JST"


class TestFormatUtcIso:
    """format_utc_iso のテスト"""
    
    def test_format_iso(self):
        """ISO 8601形式"""
        jst_dt = JST.localize(datetime(2025, 12, 27, 21, 30))
        result = DateTimeUtil.format_utc_iso(jst_dt)
        
        assert result == "2025-12-27T12:30:00Z"
