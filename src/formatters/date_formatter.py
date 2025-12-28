"""
Date formatting utilities for report generation.
"""
from datetime import datetime


class DateFormatter:
    """日付のフォーマット処理を担当するクラス"""
    
    def format_relative_date(self, iso_date: str) -> str:
        """ISO日付を「3日前」のような相対表示に変換
        
        Args:
            iso_date: ISO形式の日付文字列（例: "2025-12-19T14:00:00Z"）
            
        Returns:
            相対日付文字列（例: "3日前", "1週間前"）
        """
        if not iso_date:
            return "不明"
        try:
            import pytz
            # ISO形式をパース（2025-12-19T14:00:00Z）
            pub_date = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            jst = pytz.timezone('Asia/Tokyo')
            now = datetime.now(jst)
            diff = now - pub_date.astimezone(jst)
            
            days = diff.days
            if days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    return "数分前"
                return f"{hours}時間前"
            elif days == 1:
                return "1日前"
            elif days < 7:
                return f"{days}日前"
            elif days < 30:
                weeks = days // 7
                return f"{weeks}週間前"
            elif days < 365:
                months = days // 30
                return f"{months}ヶ月前"
            else:
                return pub_date.strftime("%Y/%m/%d")
        except Exception:
            return iso_date[:10] if len(iso_date) >= 10 else iso_date
