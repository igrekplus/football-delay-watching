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
    BEFORE_KICKOFF_MINUTES = 60    # キックオフ1時間前
    AFTER_KICKOFF_MINUTES = 1440  # キックオフ24時間後まで（失敗時の再試行余地確保）
    
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
        """現在処理対象の試合のみ抽出（時間窓のみ）
        
        キックオフ1時間前〜24時間後の試合を対象とする。
        
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
    
    def filter_processable_matches(self, matches: List, status_manager) -> List:
        """時間窓 + ステータス管理による二段階フィルタ
        
        Args:
            matches: MatchAggregateのリスト
            status_manager: FixtureStatusManager インスタンス
            
        Returns:
            処理対象試合のリスト
        """
        # ログ: 時間窓情報
        window_start = self.now - timedelta(minutes=self.BEFORE_KICKOFF_MINUTES)
        window_end = self.now + timedelta(minutes=self.AFTER_KICKOFF_MINUTES)
        
        logger.info("=" * 70)
        logger.info("試合フィルタリング開始")
        logger.info(f"現在時刻 (JST): {self.now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"時間窓: {window_start.strftime('%m/%d %H:%M')} - {window_end.strftime('%m/%d %H:%M')}")
        logger.info(f"全試合数: {len(matches)}")
        logger.info("=" * 70)
        
        # 1. 時間ウィンドウでフィルタ
        time_filtered = []
        for match in matches:
            kickoff_jst = DateTimeUtil.to_jst(match.core.kickoff_at_utc)
            in_window = self._is_in_target_window(match)
            
            log_msg = f"[Fixture {match.id}] {match.home_team} vs {match.away_team}"
            log_msg += f" | キックオフ: {kickoff_jst.strftime('%m/%d %H:%M JST')}"
            log_msg += f" | 時間窓: {'✅ 対象' if in_window else '❌ 対象外'}"
            logger.info(log_msg)
            
            if in_window:
                time_filtered.append(match)
        
        logger.info(f"時間窓フィルタ結果: {len(time_filtered)}/{len(matches)} 試合が対象")
        logger.info("-" * 70)
        
        # 2. GCSステータスでフィルタ（未処理 or 失敗で再試行可能）
        processable = []
        for match in time_filtered:
            is_processable = status_manager.is_processable(match.id)
            gcs_status = status_manager.get_status(match.id) or "なし（初回処理）"
            
            log_msg = f"[Fixture {match.id}] {match.home_team} vs {match.away_team}"
            log_msg += f" | GCSステータス: {gcs_status}"
            log_msg += f" | 処理可能: {'✅ Yes' if is_processable else '❌ No'}"
            logger.info(log_msg)
            
            if is_processable:
                processable.append(match)
        
        logger.info(f"ステータスフィルタ結果: {len(processable)}/{len(time_filtered)} 試合が処理可能")
        logger.info("-" * 70)
        
        # 3. ランク順でソートし、上位MAX_MATCHES_PER_DAY件を返す
        processable.sort(key=lambda m: self._get_rank_priority(m))
        
        if len(processable) > self.MAX_MATCHES_PER_DAY:
            logger.info(f"試合数制限適用: {len(processable)} → {self.MAX_MATCHES_PER_DAY}")
            excluded = processable[self.MAX_MATCHES_PER_DAY:]
            for match in excluded:
                logger.info(f"  除外: [Fixture {match.id}] {match.home_team} vs {match.away_team} (Rank {match.rank})")
            processable = processable[:self.MAX_MATCHES_PER_DAY]
        
        logger.info("=" * 70)
        logger.info(f"最終選定: {len(processable)} 試合")
        for match in processable:
            logger.info(f"  選定: [Fixture {match.id}] {match.home_team} vs {match.away_team} (Rank {match.rank})")
        logger.info("=" * 70)
        
        return processable
    
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
