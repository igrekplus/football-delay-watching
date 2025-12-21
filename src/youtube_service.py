"""
YouTube動画取得サービス

試合前の関連動画（記者会見、過去の名勝負、戦術解説、練習風景）を
YouTube Data API v3で取得する。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests

import os

from config import config
from settings.channels import (
    get_team_channel,
    LEAGUE_CHANNELS,
    BROADCASTER_CHANNELS,
    TACTICS_CHANNELS,
)
from src.domain.models import MatchData

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube動画を取得するサービス"""
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    MAX_RESULTS_PER_CATEGORY = 3
    
    def __init__(self, api_key: str = None):
        # YOUTUBE_API_KEY を優先、なければ GOOGLE_API_KEY にフォールバック
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or config.GOOGLE_API_KEY
        self._channel_id_cache: Dict[str, str] = {}
    
    def _resolve_channel_id(self, handle: str) -> Optional[str]:
        """ハンドル名(@xxx)からチャンネルIDを解決"""
        if handle in self._channel_id_cache:
            return self._channel_id_cache[handle]
        
        # ハンドル名の@を除去
        clean_handle = handle.lstrip("@")
        
        try:
            url = f"{self.API_BASE}/channels"
            params = {
                "key": self.api_key,
                "forHandle": clean_handle,
                "part": "id",
            }
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("items"):
                    channel_id = data["items"][0]["id"]
                    self._channel_id_cache[handle] = channel_id
                    return channel_id
        except Exception as e:
            logger.warning(f"Failed to resolve channel ID for {handle}: {e}")
        
        return None
    
    def _search_videos(
        self,
        query: str,
        channel_id: Optional[str] = None,
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None,
        max_results: int = 3,
    ) -> List[Dict]:
        """YouTube検索を実行"""
        try:
            url = f"{self.API_BASE}/search"
            params = {
                "key": self.api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": max_results,
                "order": "relevance",
            }
            
            if channel_id:
                params["channelId"] = channel_id
            
            if published_after:
                params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            if published_before:
                params["publishedBefore"] = published_before.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("items", []):
                    video_id = item["id"].get("videoId")
                    if video_id:
                        results.append({
                            "video_id": video_id,
                            "title": item["snippet"]["title"],
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "channel_name": item["snippet"]["channelTitle"],
                            "thumbnail_url": item["snippet"]["thumbnails"]["medium"]["url"],
                            "published_at": item["snippet"]["publishedAt"],
                        })
                return results
            else:
                logger.warning(f"YouTube search failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        
        return []
    
    def _search_press_conference(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """記者会見を検索"""
        results = []
        channel_handle = get_team_channel(team_name)
        channel_id = self._resolve_channel_id(channel_handle) if channel_handle else None
        
        # 48時間前〜キックオフ
        published_after = kickoff_time - timedelta(hours=48)
        
        for query in [f"{team_name} press conference", f"{team_name} 記者会見"]:
            videos = self._search_videos(
                query=query,
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            )
            for v in videos:
                v["category"] = "press_conference"
            results.extend(videos)
        
        return results[:self.MAX_RESULTS_PER_CATEGORY]
    
    def _search_historic_clashes(
        self,
        home_team: str,
        away_team: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """過去の名勝負・対戦ハイライトを検索（当日のプレビューではなく過去試合）"""
        results = []
        
        # 過去2年〜キックオフまでの動画を検索
        # "highlights"キーワードで試合後のハイライト動画を特定
        published_after = kickoff_time - timedelta(days=730)  # 2年前
        published_before = kickoff_time  # キックオフまで
        
        # ハイライト系キーワードで検索（プレビューではなく過去試合結果）
        for query in [
            f"{home_team} vs {away_team} highlights",
            f"{home_team} {away_team} extended highlights",
        ]:
            videos = self._search_videos(
                query=query,
                published_after=published_after,
                published_before=published_before,
                max_results=3,
            )
            for v in videos:
                v["category"] = "historic"
            results.extend(videos)
        
        return results[:self.MAX_RESULTS_PER_CATEGORY]
    
    def _search_tactical(
        self,
        team_name: str,
        players: List[str],
        kickoff_time: datetime,
    ) -> List[Dict]:
        """戦術・選手プレー集を検索"""
        results = []
        
        # 直近1ヶ月〜キックオフ
        published_after = kickoff_time - timedelta(days=30)
        
        # 戦術チャンネルで検索
        for handle in TACTICS_CHANNELS.values():
            channel_id = self._resolve_channel_id(handle)
            if not channel_id:
                continue
            
            # チーム戦術
            videos = self._search_videos(
                query=f"{team_name} tactics analysis",
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            )
            for v in videos:
                v["category"] = "tactical"
            results.extend(videos)
        
        # 選手プレー集（各チーム3人）
        for player in players[:3]:
            videos = self._search_videos(
                query=f"{player} skills",
                published_after=published_after,
                published_before=kickoff_time,
                max_results=1,
            )
            for v in videos:
                v["category"] = "tactical"
            results.extend(videos)
        
        return results[:self.MAX_RESULTS_PER_CATEGORY]
    
    def _search_training(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """練習風景を検索"""
        results = []
        channel_handle = get_team_channel(team_name)
        channel_id = self._resolve_channel_id(channel_handle) if channel_handle else None
        
        # 48時間前〜キックオフ
        published_after = kickoff_time - timedelta(hours=48)
        
        for query in [f"{team_name} training", f"{team_name} 練習"]:
            videos = self._search_videos(
                query=query,
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            )
            for v in videos:
                v["category"] = "training"
            results.extend(videos)
        
        return results[:self.MAX_RESULTS_PER_CATEGORY]
    
    def _deduplicate(self, videos: List[Dict]) -> List[Dict]:
        """重複を排除"""
        seen = set()
        unique = []
        for v in videos:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                unique.append(v)
        return unique
    
    def _get_key_players(self, match: MatchData) -> tuple[List[str], List[str]]:
        """各チームのキープレイヤー3人を取得（FW/MF優先）"""
        home_players = []
        away_players = []
        
        # ホームチーム
        if hasattr(match, 'home_players') and match.home_players:
            # FW, MF, DF の順で優先
            for pos in ["FW", "MF", "DF", "GK"]:
                for p in match.home_players:
                    if p.get("position", "").startswith(pos) and len(home_players) < 3:
                        home_players.append(p.get("name", ""))
        
        # アウェイチーム
        if hasattr(match, 'away_players') and match.away_players:
            for pos in ["FW", "MF", "DF", "GK"]:
                for p in match.away_players:
                    if p.get("position", "").startswith(pos) and len(away_players) < 3:
                        away_players.append(p.get("name", ""))
        
        return home_players, away_players
    
    def get_videos_for_match(self, match: MatchData) -> List[Dict]:
        """試合に関連する動画を取得"""
        all_videos = []
        
        home_team = match.home_team
        away_team = match.away_team
        # kickoff_jstは "2025/12/21 00:00 JST" 形式の文字列
        # JSTとしてパースしてUTCに変換
        from datetime import datetime
        import pytz
        try:
            jst = pytz.timezone('Asia/Tokyo')
            kickoff_naive = datetime.strptime(
                match.kickoff_jst.replace(" JST", ""), "%Y/%m/%d %H:%M"
            )
            # JSTとしてタイムゾーンを設定してUTCに変換
            kickoff_time = jst.localize(kickoff_naive).astimezone(pytz.UTC)
            logger.info(f"Kickoff time: {match.kickoff_jst} -> UTC: {kickoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse kickoff_jst: {e}")
            kickoff_time = datetime.now(pytz.UTC)
        
        logger.info(f"Fetching YouTube videos for {home_team} vs {away_team}")
        
        # キープレイヤーを取得
        home_players, away_players = self._get_key_players(match)
        
        # 1. 記者会見
        all_videos.extend(self._search_press_conference(home_team, kickoff_time))
        all_videos.extend(self._search_press_conference(away_team, kickoff_time))
        
        # 2. 因縁
        all_videos.extend(self._search_historic_clashes(home_team, away_team, kickoff_time))
        
        # 3. 戦術
        all_videos.extend(self._search_tactical(home_team, home_players, kickoff_time))
        all_videos.extend(self._search_tactical(away_team, away_players, kickoff_time))
        
        # 4. 練習風景
        all_videos.extend(self._search_training(home_team, kickoff_time))
        all_videos.extend(self._search_training(away_team, kickoff_time))
        
        # 重複排除
        unique_videos = self._deduplicate(all_videos)
        
        logger.info(f"Found {len(unique_videos)} unique videos for {home_team} vs {away_team}")
        
        return unique_videos
    
    def process_matches(self, matches: List[MatchData]) -> Dict[str, List[Dict]]:
        """全試合の動画を取得"""
        results = {}
        
        for match in matches:
            match_key = f"{match.home_team} vs {match.away_team}"
            results[match_key] = self.get_videos_for_match(match)
        
        return results
