"""
Date formatting utilities for report generation.

Note: 実際のロジックは DateTimeUtil に統合されています。
このクラスは後方互換のために残されています。
"""
from src.utils.datetime_util import DateTimeUtil


class DateFormatter:
    """日付のフォーマット処理を担当するクラス
    
    Note: Issue #88 により DateTimeUtil への移行を推奨します。
    このクラスは後方互換のために残されています。
    """
    
    def format_relative_date(self, iso_date: str) -> str:
        """ISO日付を「3日前」のような相対表示に変換
        
        Args:
            iso_date: ISO形式の日付文字列（例: "2025-12-19T14:00:00Z"）
            
        Returns:
            相対日付文字列（例: "3日前", "1週間前"）
        
        Note:
            DateTimeUtil.format_relative_date() への委譲。
        """
        return DateTimeUtil.format_relative_date(iso_date)
