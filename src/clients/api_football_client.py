"""
API-Football クライアント

API-Footballとのやり取りを一元化する。
ServiceはこのClientを通じてサッカーデータを取得する。
"""

import logging
from typing import Dict, List, Any, Optional

import pytz
from datetime import datetime

from config import config
from src.clients.cache import get_with_cache

logger = logging.getLogger(__name__)


class ApiFootballClient:
    """API-Football クライアント"""
    
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: API-Football Key
        """
        self.api_key = api_key or config.API_FOOTBALL_KEY
        self.headers = {"x-apisports-key": self.api_key}
    
    def _get_current_season(self) -> int:
        """現在のシーズン年を取得（8月以降は今年、それ以前は前年）"""
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        return now.year if now.month >= 8 else now.year - 1
    
    def fetch_fixtures(
        self, 
        league_id: int = None, 
        date: str = None,
        fixture_id: int = None
    ) -> Dict[str, Any]:
        """
        試合情報を取得
        
        Args:
            league_id: リーグID
            date: 日付（YYYY-MM-DD形式）
            fixture_id: 試合ID（単一試合取得時）
        """
        url = f"{self.BASE_URL}/fixtures"
        params = {}
        
        if fixture_id:
            params["id"] = fixture_id
        else:
            if league_id:
                params["league"] = league_id
            if date:
                params["date"] = date
        
        try:
            response = get_with_cache(url, headers=self.headers, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching fixtures: {e}")
            return {"response": []}
    
    def fetch_lineups(self, fixture_id: int) -> Dict[str, Any]:
        """
        スタメン情報を取得
        
        Args:
            fixture_id: 試合ID
            
        Returns:
            APIレスポンス
        """
        url = f"{self.BASE_URL}/fixtures/lineups"
        params = {"fixture": fixture_id}
        
        try:
            response = get_with_cache(url, headers=self.headers, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching lineups for fixture {fixture_id}: {e}")
            return {"response": []}
    
    def fetch_injuries(self, fixture_id: int) -> Dict[str, Any]:
        """
        怪我人情報を取得
        
        Args:
            fixture_id: 試合ID
        """
        url = f"{self.BASE_URL}/injuries"
        params = {"fixture": fixture_id}
        
        try:
            response = get_with_cache(url, headers=self.headers, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching injuries for fixture {fixture_id}: {e}")
            return {"response": []}
    
    def fetch_team_statistics(
        self, 
        team_id: int, 
        league_id: int,
        season: int = None
    ) -> Dict[str, Any]:
        """
        チーム統計情報を取得
        
        Args:
            team_id: チームID
            league_id: リーグID
            season: シーズン年（省略時は現在のシーズン）
        """
        url = f"{self.BASE_URL}/teams/statistics"
        season = season or self._get_current_season()
        params = {
            "team": team_id,
            "season": season,
            "league": league_id
        }
        
        try:
            response = get_with_cache(url, headers=self.headers, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching team statistics for team {team_id}: {e}")
            return {"response": {}}
    
    def fetch_h2h(self, team1_id: int, team2_id: int, last: int = 5) -> Dict[str, Any]:
        """
        対戦履歴を取得
        
        Args:
            team1_id: チーム1のID
            team2_id: チーム2のID
            last: 取得する試合数
        """
        url = f"{self.BASE_URL}/fixtures/headtohead"
        params = {
            "h2h": f"{team1_id}-{team2_id}",
            "last": last
        }
        
        try:
            response = get_with_cache(url, headers=self.headers, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching H2H for {team1_id}-{team2_id}: {e}")
            return {"response": []}
    
    def fetch_player_details(
        self, 
        player_id: int, 
        season: int = None,
        team_name: str = None
    ) -> Dict[str, Any]:
        """
        選手詳細情報を取得
        
        Args:
            player_id: 選手ID
            season: シーズン年
            team_name: チーム名（キャッシュキー用）
        """
        url = f"{self.BASE_URL}/players"
        season = season or self._get_current_season()
        params = {"id": player_id, "season": season}
        
        try:
            response = get_with_cache(
                url, 
                headers=self.headers, 
                params=params,
                team_name=team_name
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching player details for {player_id}: {e}")
            return {"response": []}
