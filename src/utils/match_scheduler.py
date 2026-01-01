"""
試合スケジューラ

試合時刻に基づく実行判定ロジックを提供する。
キックオフ1時間前〜直後の試合を対象とする。
"""

import logging
from typing import List
from datetime import datetime, timedelta

from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)


class MatchScheduler:
    """試合時刻に基づく実行判定"""
    
    # 試合対象の時間ウィンドウ（分）
    BEFORE_KICKOFF_MINUTES = 60  # キックオフ1時間前
    AFTER_KICKOFF_MINUTES = 30   # キックオフ30分後まで
    
    # 1日の最大試合数
    MAX_MATCHES_PER_DAY = 5
    
    def __init__(self):
        self.now = DateTimeUtil.now_jst()
    
    def should_generate_report(self, matches: List) -> bool:
        """現在時刻で処理すべき試合があるか判定
        
        Args:
            matches: MatchAggregateのリスト
            
        Returns:
            処理すべき試合があればTrue
        """
        current_matches = self.filter_current_matches(matches)
        return len(current_matches) > 0
    
    def filter_current_matches(self, matches: List) -> List:
        """現在処理対象の試合のみ抽出
        
        キックオフ1時間前〜30分後の試合を対象とする。
        
        Args:
            matches: MatchAggregateのリスト
            
        Returns:
            対象試合のリスト
        """
        current_matches = []
        
        for match in matches:
            if self._is_in_target_window(match):
                current_matches.append(match)
        
        # ランク順でソートし、上位MAX_MATCHES_PER_DAY件を返す
        current_matches.sort(key=lambda m: self._get_rank_priority(m))
        
        if len(current_matches) > self.MAX_MATCHES_PER_DAY:
            logger.info(f"試合数制限: {len(current_matches)} → {self.MAX_MATCHES_PER_DAY}")
            current_matches = current_matches[:self.MAX_MATCHES_PER_DAY]
        
        return current_matches
    
    def _is_in_target_window(self, match) -> bool:
        """試合が対象時間ウィンドウ内かどうか"""
        try:
            # MatchAggregate.core.kickoff_at_utc を使用
            kickoff_utc = match.core.kickoff_at_utc
            if kickoff_utc is None:
                logger.warning(f"kickoff_at_utc is None for match {match.id}")
                return False
            
            kickoff_jst = DateTimeUtil.to_jst(kickoff_utc)
            
            window_start = kickoff_jst - timedelta(minutes=self.BEFORE_KICKOFF_MINUTES)
            window_end = kickoff_jst + timedelta(minutes=self.AFTER_KICKOFF_MINUTES)
            
            is_in_window = window_start <= self.now <= window_end
            
            if is_in_window:
                logger.debug(f"Match {match.id} is in target window: {window_start} - {window_end}")
            
            return is_in_window
            
        except Exception as e:
            logger.warning(f"Failed to check target window for match: {e}")
            return False
    
    def _get_rank_priority(self, match) -> int:
        """ランクを優先度に変換（S=0, A=1, B=2, ...）"""
        rank_order = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4}
        rank = getattr(match, 'rank', None) or getattr(match.core, 'rank', 'D')
        return rank_order.get(rank, 5)
    
    def get_upcoming_matches(self, matches: List, hours_ahead: int = 24) -> List:
        """今後N時間以内にキックオフする試合を取得
        
        Args:
            matches: MatchAggregateのリスト
            hours_ahead: 先読みする時間数
            
        Returns:
            対象試合のリスト
        """
        upcoming = []
        cutoff = self.now + timedelta(hours=hours_ahead)
        
        for match in matches:
            try:
                kickoff_utc = match.core.kickoff_at_utc
                if kickoff_utc is None:
                    continue
                
                kickoff_jst = DateTimeUtil.to_jst(kickoff_utc)
                
                if self.now <= kickoff_jst <= cutoff:
                    upcoming.append(match)
            except Exception:
                continue
        
        return upcoming
