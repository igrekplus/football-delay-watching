"""
日時ユーティリティ

Issue #70: 日時/タイムゾーン処理の一元化
- kickoff_jst文字列のパース（複数フォーマット対応）
- タイムゾーン変換
- 表示用文字列生成
"""

import re
import logging
from datetime import datetime
from typing import Optional

import pytz

logger = logging.getLogger(__name__)

# タイムゾーン定数
JST = pytz.timezone('Asia/Tokyo')
UTC = pytz.UTC


class DateTimeUtil:
    """日時変換ユーティリティ"""
    
    # kickoff_jst の既知フォーマット
    # 優先度順にリスト（より具体的なものを先に）
    KICKOFF_JST_FORMATS = [
        # "2025/12/27(土) 21:30 JST" - 曜日あり
        (r"^(\d{4}/\d{2}/\d{2})\([月火水木金土日]\)\s*(\d{2}:\d{2})\s*JST$", "%Y/%m/%d %H:%M"),
        # "2025/12/21 00:00 JST" - 曜日なし
        (r"^(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2})\s*JST$", "%Y/%m/%d %H:%M"),
    ]
    
    @staticmethod
    def parse_kickoff_jst(kickoff_jst: str) -> Optional[datetime]:
        """
        kickoff_jst 文字列を timezone-aware datetime (UTC) に変換
        
        サポートするフォーマット:
        - "2025/12/27(土) 21:30 JST" (曜日あり)
        - "2025/12/21 00:00 JST" (曜日なし)
        
        Args:
            kickoff_jst: JST時刻文字列
            
        Returns:
            timezone-aware datetime (UTC)、パース失敗時は None
        """
        if not kickoff_jst:
            return None
        
        for pattern, date_format in DateTimeUtil.KICKOFF_JST_FORMATS:
            match = re.match(pattern, kickoff_jst.strip())
            if match:
                # 日付部分と時刻部分を結合
                date_part = match.group(1)
                time_part = match.group(2)
                datetime_str = f"{date_part} {time_part}"
                
                try:
                    # naiveなdatetimeとしてパース
                    naive_dt = datetime.strptime(datetime_str, date_format)
                    # JSTとしてローカライズ
                    jst_dt = JST.localize(naive_dt)
                    # UTCに変換
                    utc_dt = jst_dt.astimezone(UTC)
                    return utc_dt
                except ValueError as e:
                    logger.warning(f"Failed to parse kickoff_jst with format {date_format}: {e}")
                    continue
        
        logger.warning(f"No matching format for kickoff_jst: {kickoff_jst}")
        return None
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """
        任意のtimezone-aware datetime を UTC に変換
        
        Args:
            dt: timezone-aware datetime
            
        Returns:
            UTC datetime
        """
        if dt.tzinfo is None:
            # naiveな場合はJSTと仮定
            dt = JST.localize(dt)
        return dt.astimezone(UTC)
    
    @staticmethod
    def to_jst(dt: datetime) -> datetime:
        """
        任意のtimezone-aware datetime を JST に変換
        
        Args:
            dt: timezone-aware datetime
            
        Returns:
            JST datetime
        """
        if dt.tzinfo is None:
            # naiveな場合はUTCと仮定
            dt = UTC.localize(dt)
        return dt.astimezone(JST)
    
    @staticmethod
    def format_jst_display(dt: datetime, include_weekday: bool = True) -> str:
        """
        datetime を表示用JST文字列に変換
        
        Args:
            dt: timezone-aware datetime
            include_weekday: 曜日を含めるか
            
        Returns:
            表示用文字列（例: "2025/12/27(土) 21:30 JST"）
        """
        jst_dt = DateTimeUtil.to_jst(dt)
        
        if include_weekday:
            weekday_ja = ['月', '火', '水', '木', '金', '土', '日'][jst_dt.weekday()]
            return jst_dt.strftime(f"%Y/%m/%d({weekday_ja}) %H:%M JST")
        else:
            return jst_dt.strftime("%Y/%m/%d %H:%M JST")
    
    @staticmethod
    def format_utc_iso(dt: datetime) -> str:
        """
        datetime を ISO 8601 UTC形式に変換
        
        Args:
            dt: timezone-aware datetime
            
        Returns:
            ISO 8601形式（例: "2025-12-27T12:30:00Z"）
        """
        utc_dt = DateTimeUtil.to_utc(dt)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # --- Issue #88: 追加メソッド ---
    
    @staticmethod
    def now_jst() -> datetime:
        """
        現在時刻をJSTで取得
        
        Returns:
            timezone-aware datetime (JST)
        """
        return datetime.now(JST)
    
    @staticmethod
    def format_filename_datetime(dt: datetime = None) -> str:
        """
        ファイル名用フォーマット
        
        Args:
            dt: timezone-aware datetime（省略時は現在時刻）
            
        Returns:
            ファイル名用文字列（例: "20251228_072100"）
        """
        if dt is None:
            dt = DateTimeUtil.now_jst()
        jst_dt = DateTimeUtil.to_jst(dt)
        return jst_dt.strftime('%Y%m%d_%H%M%S')
    
    @staticmethod
    def format_date_str(dt: datetime) -> str:
        """
        API用日付文字列
        
        Args:
            dt: timezone-aware datetime
            
        Returns:
            日付文字列（例: "2025-12-28"）
        """
        jst_dt = DateTimeUtil.to_jst(dt)
        return jst_dt.strftime('%Y-%m-%d')
    
    @staticmethod
    def format_display_timestamp(dt: datetime = None) -> str:
        """
        表示用タイムスタンプ
        
        Args:
            dt: timezone-aware datetime（省略時は現在時刻）
            
        Returns:
            表示用文字列（例: "2025-12-28 07:21:00 JST"）
        """
        if dt is None:
            dt = DateTimeUtil.now_jst()
        jst_dt = DateTimeUtil.to_jst(dt)
        return jst_dt.strftime('%Y-%m-%d %H:%M:%S JST')
    
    @staticmethod
    def get_weekday_ja(dt: datetime) -> str:
        """
        日本語曜日を取得
        
        Args:
            dt: timezone-aware datetime
            
        Returns:
            日本語曜日（例: "土"）
        """
        jst_dt = DateTimeUtil.to_jst(dt)
        return ['月', '火', '水', '木', '金', '土', '日'][jst_dt.weekday()]
    
    @staticmethod
    def format_relative_date(iso_date: str) -> str:
        """
        ISO日付を「3日前」のような相対表示に変換
        
        Args:
            iso_date: ISO形式の日付文字列（例: "2025-12-19T14:00:00Z"）
            
        Returns:
            相対日付文字列（例: "3日前", "1週間前"）
        """
        if not iso_date:
            return "不明"
        try:
            # ISO形式をパース（2025-12-19T14:00:00Z）
            pub_date = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            now = DateTimeUtil.now_jst()
            diff = now - pub_date.astimezone(JST)
            
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

