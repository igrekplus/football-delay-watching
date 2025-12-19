"""
キャッシュウォーミングモジュール

試合がない日に上位チームの選手データをGCSにプリフェッチし、
週末の試合レポート生成時にキャッシュHITさせることでAPI消費を削減する。
"""

import logging
from typing import List, Dict, Set
from datetime import datetime
import pytz

from config import config
from src.clients.cache import get_with_cache, CACHE_BACKEND

logger = logging.getLogger(__name__)


class CacheWarmer:
    """上位チームの選手データをキャッシュするクラス"""
    
    def __init__(self):
        self.api_base = "https://api-football-v1.p.rapidapi.com/v3"
        self.headers = {
            "X-RapidAPI-Key": config.RAPIDAPI_KEY,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        self.requests_made = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _check_time_limit(self) -> bool:
        """09:00 JST（クォータリセット時間）前かどうか確認"""
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        # 09:00 JSTの5分前（08:55）までに完了させる
        if now.hour >= 8 and now.minute >= 55:
            logger.warning("Approaching quota reset time (09:00 JST). Stopping cache warming.")
            return False
        return True
    
    def _get_squad(self, team_id: int, team_name: str) -> List[Dict]:
        """チームのスクワッド（全選手リスト）を取得"""
        url = f"{self.api_base}/players/squads"
        params = {"team": team_id}
        
        try:
            response = get_with_cache(url, self.headers, params, team_name=team_name)
            self.requests_made += 1
            
            if response.status_code == 200:
                data = response.json()
                if data.get("response") and len(data["response"]) > 0:
                    return data["response"][0].get("players", [])
        except Exception as e:
            logger.error(f"Failed to get squad for {team_name}: {e}")
        
        return []
    
    def _cache_player(self, player_id: int, team_name: str, remaining_quota: int) -> bool:
        """選手の詳細情報をキャッシュ（未キャッシュの場合のみAPIコール）"""
        if remaining_quota <= 0:
            return False
            
        url = f"{self.api_base}/players"
        params = {"id": player_id, "season": 2024}
        
        try:
            response = get_with_cache(url, self.headers, params, team_name=team_name)
            self.requests_made += 1
            
            # キャッシュヒットかミスかをログから判定
            # (get_with_cacheがCachedResponseを返す場合はキャッシュヒット)
            if hasattr(response, '_json_data'):
                self.cache_hits += 1
            else:
                self.cache_misses += 1
                
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to cache player {player_id}: {e}")
            return False
    
    def run(self, remaining_quota: int) -> Dict:
        """
        キャッシュウォーミングを実行
        
        Args:
            remaining_quota: 残りAPIクォータ
            
        Returns:
            実行結果の統計情報
        """
        if remaining_quota < config.CACHE_WARMING_QUOTA_THRESHOLD:
            logger.info(f"Skipping cache warming: quota {remaining_quota} < threshold {config.CACHE_WARMING_QUOTA_THRESHOLD}")
            return {"skipped": True, "reason": "quota_low"}
        
        if not self._check_time_limit():
            return {"skipped": True, "reason": "time_limit"}
        
        logger.info(f"Starting cache warming with {remaining_quota} remaining quota")
        
        # EPLとCLのチームを統合（重複除去）
        all_teams: Set[tuple] = set()
        all_teams.update(config.EPL_CACHE_TEAMS)
        all_teams.update(config.CL_CACHE_TEAMS)
        
        logger.info(f"Target teams: {len(all_teams)} unique teams")
        
        players_processed = 0
        available_quota = remaining_quota - config.CACHE_WARMING_QUOTA_THRESHOLD  # 安全マージン
        
        for team_id, team_name in all_teams:
            if not self._check_time_limit():
                break
                
            if available_quota <= 0:
                logger.info("Quota limit reached. Stopping cache warming.")
                break
            
            logger.info(f"Processing team: {team_name} (ID: {team_id})")
            
            # スクワッド取得
            squad = self._get_squad(team_id, team_name)
            available_quota -= 1
            
            if not squad:
                logger.warning(f"No squad data for {team_name}")
                continue
            
            # 各選手をキャッシュ
            for player in squad:
                if not self._check_time_limit():
                    break
                    
                if available_quota <= 0:
                    break
                    
                player_id = player.get("id")
                if player_id:
                    self._cache_player(player_id, team_name, available_quota)
                    available_quota -= 1
                    players_processed += 1
        
        result = {
            "skipped": False,
            "teams_processed": len(all_teams),
            "players_processed": players_processed,
            "requests_made": self.requests_made,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }
        
        logger.info(f"Cache warming completed: {result}")
        return result


def run_cache_warming(remaining_quota: int) -> Dict:
    """キャッシュウォーミングを実行するエントリーポイント"""
    import os
    
    # Check if cache warming is enabled via environment variable
    cache_warming_enabled = os.getenv("CACHE_WARMING_ENABLED", "False").lower() == "true"
    if not cache_warming_enabled:
        logger.info("Cache warming skipped: CACHE_WARMING_ENABLED is False")
        return {"skipped": True, "reason": "disabled"}
    
    if config.USE_MOCK_DATA:
        logger.info("Cache warming skipped: mock mode")
        return {"skipped": True, "reason": "mock_mode"}
    
    if CACHE_BACKEND != "gcs":
        logger.info("Cache warming skipped: GCS backend not enabled")
        return {"skipped": True, "reason": "no_gcs"}
    
    warmer = CacheWarmer()
    return warmer.run(remaining_quota)
