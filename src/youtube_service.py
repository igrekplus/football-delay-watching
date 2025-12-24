"""
YouTube動画取得サービス

試合前の関連動画（記者会見、過去の名勝負、戦術解説、練習風景、選手紹介）を
YouTube Data API v3で取得する。

キャッシュ: 1週間TTLでローカルに保存し、開発中のクォータ消費を抑制。

Issue #27: クエリ削減（20→13/試合）とpost-fetchフィルタ方式への移行
"""

import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import requests
import os

from config import config
from settings.channels import (
    get_team_channel,
    is_trusted_channel,
    get_channel_info,
    TACTICS_CHANNELS,  # 後方互換性のため残す（将来削除予定）
)
from src.domain.models import MatchData

logger = logging.getLogger(__name__)

# YouTube検索結果のキャッシュ設定
YOUTUBE_CACHE_DIR = Path("api_cache/youtube")
YOUTUBE_CACHE_TTL_HOURS = 168  # キャッシュ有効期限（1週間）


class YouTubeService:
    """YouTube動画を取得するサービス"""
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    # チューニング可能なパラメータ
    HISTORIC_SEARCH_DAYS = 730      # 過去ハイライト検索期間（2年）
    RECENT_SEARCH_HOURS = 48        # 公式動画検索期間（48時間）
    TRAINING_SEARCH_HOURS = 168     # 練習動画検索期間（1週間）
    TACTICAL_SEARCH_DAYS = 180      # 戦術動画検索期間（6ヶ月）
    PLAYER_SEARCH_DAYS = 180        # 選手紹介動画検索期間（6ヶ月）
    
    # post-fetch用: 取得件数（フィルタ後に絞り込む）
    FETCH_MAX_RESULTS = 10
    
    def __init__(self, api_key: str = None):
        # YOUTUBE_API_KEY を優先、なければ GOOGLE_API_KEY にフォールバック
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or config.GOOGLE_API_KEY
        self._channel_id_cache: Dict[str, str] = {}
    
    def _get_cache_key(self, query: str, channel_id: Optional[str], 
                       published_after: Optional[datetime], 
                       published_before: Optional[datetime]) -> str:
        """検索条件からキャッシュキーを生成"""
        key_parts = [
            query,
            channel_id or "",
            published_after.strftime("%Y%m%d") if published_after else "",
            published_before.strftime("%Y%m%d") if published_before else "",
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _read_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """キャッシュから読み込み（TTLチェック付き）"""
        cache_file = YOUTUBE_CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # TTLチェック
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(hours=YOUTUBE_CACHE_TTL_HOURS):
                logger.debug(f"Cache expired: {cache_key}")
                return None
            
            logger.info(f"YouTube cache HIT: {cache_key[:8]}...")
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"Failed to read YouTube cache: {e}")
            return None
    
    def _write_cache(self, cache_key: str, results: List[Dict]):
        """キャッシュに書き込み"""
        try:
            YOUTUBE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = YOUTUBE_CACHE_DIR / f"{cache_key}.json"
            
            data = {
                "cached_at": datetime.now().isoformat(),
                "results": results,
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"YouTube cache saved: {cache_key[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to write YouTube cache: {e}")
    
    def _search_videos(
        self,
        query: str,
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None,
        max_results: int = 10,
        relevance_language: Optional[str] = None,
    ) -> List[Dict]:
        """
        YouTube検索を実行（1週間キャッシュ付き）
        
        post-fetch方式: チャンネル指定なしで検索し、後からフィルタ
        
        Args:
            relevance_language: 結果の言語優先度（ISO 639-1、例: "ja"）
        """
        
        # キャッシュチェック（チャンネルIDなしで検索するため、channel_id=None）
        # relevance_languageもキャッシュキーに含める
        cache_key = self._get_cache_key(query + (relevance_language or ""), None, published_after, published_before)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached[:max_results]
        
        # API呼び出し
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
            
            if published_after:
                params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            if published_before:
                params["publishedBefore"] = published_before.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            if relevance_language:
                params["relevanceLanguage"] = relevance_language
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for i, item in enumerate(data.get("items", [])):
                    video_id = item["id"].get("videoId")
                    if video_id:
                        results.append({
                            "video_id": video_id,
                            "title": item["snippet"]["title"],
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "channel_id": item["snippet"]["channelId"],
                            "channel_name": item["snippet"]["channelTitle"],
                            "thumbnail_url": item["snippet"]["thumbnails"]["medium"]["url"],
                            "published_at": item["snippet"]["publishedAt"],
                            "original_index": i,  # relevance順を保持
                        })
                
                # キャッシュ保存
                self._write_cache(cache_key, results)
                logger.info(f"YouTube API: '{query}' -> {len(results)} results")
                
                return results
            else:
                logger.warning(f"YouTube search failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        
        return []
    
    def _apply_trusted_channel_filter(self, videos: List[Dict]) -> List[Dict]:
        """
        信頼チャンネル優先でソート + バッジ付与
        
        チューニング中は全件出力、信頼チャンネルにはバッジを付与
        """
        for v in videos:
            channel_id = v.get("channel_id", "")
            v["is_trusted"] = is_trusted_channel(channel_id)
            
            if v["is_trusted"]:
                info = get_channel_info(channel_id)
                v["channel_display"] = f"✅ {info['name']}"
                logger.info(f"YouTube result: \"{v['title'][:30]}...\" by {info['name']} (✅ trusted)")
            else:
                v["channel_display"] = f"⚠️ {v.get('channel_name', 'Unknown')}"
                logger.info(f"YouTube result: \"{v['title'][:30]}...\" by {v.get('channel_name', 'Unknown')} (⚠️ not trusted)")
        
        # ソート: 信頼チャンネル優先、その中ではrelevance順維持
        videos.sort(key=lambda v: (
            0 if v["is_trusted"] else 1,
            v.get("original_index", 0)
        ))
        
        return videos
    
    def _search_press_conference(
        self,
        team_name: str,
        manager_name: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """
        記者会見を検索
        
        変更: 日本語クエリ削除、監督名追加、post-fetchフィルタ
        クエリ数: 1クエリ/チーム
        """
        # 48時間前〜キックオフ
        published_after = kickoff_time - timedelta(hours=self.RECENT_SEARCH_HOURS)
        
        # 監督名がある場合は含める
        if manager_name:
            query = f"{team_name} {manager_name} press conference"
        else:
            query = f"{team_name} press conference"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=kickoff_time,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = "press_conference"
        
        # post-fetchフィルタ適用
        return self._apply_trusted_channel_filter(videos)
    
    def _search_historic_clashes(
        self,
        home_team: str,
        away_team: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """
        過去の名勝負・対戦ハイライトを検索
        
        変更: extended highlights クエリ削除、post-fetchフィルタ
        クエリ数: 1クエリ
        """
        # 過去2年〜キックオフまでの動画を検索
        published_after = kickoff_time - timedelta(days=self.HISTORIC_SEARCH_DAYS)
        published_before = kickoff_time
        
        query = f"{home_team} vs {away_team} highlights"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = "historic"
        
        # post-fetchフィルタ適用
        return self._apply_trusted_channel_filter(videos)
    
    def _search_tactical(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """
        戦術分析を検索
        
        変更: 日本語のみ、戦術チャンネル指定なし（post-fetch）、選手検索は分離
        クエリ数: 1クエリ/チーム
        """
        published_after = kickoff_time - timedelta(days=self.TACTICAL_SEARCH_DAYS)
        
        # 日本語のみで検索
        query = f"{team_name} 戦術 分析"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=kickoff_time,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = "tactical"
        
        # post-fetchフィルタ適用
        return self._apply_trusted_channel_filter(videos)
    
    def _search_player_highlight(
        self,
        player_name: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """
        選手紹介動画を検索（新規カテゴリ）
        
        クエリ: 選手名のみ
        クエリ数: 1クエリ/選手
        """
        published_after = kickoff_time - timedelta(days=self.PLAYER_SEARCH_DAYS)
        
        # 選手名 + 日本語で検索して日本語コンテンツも拾う
        # 名前のフルネームを使用（略称ではなく）
        query = f"{player_name} ハイライト"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=kickoff_time,
            max_results=self.FETCH_MAX_RESULTS,
            relevance_language="ja",
        )
        
        for v in videos:
            v["category"] = "player_highlight"
        
        # post-fetchフィルタ適用
        return self._apply_trusted_channel_filter(videos)
    
    def _search_training(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> List[Dict]:
        """
        練習風景を検索
        
        変更: 日本語クエリ + relevanceLanguage=ja、期間を1週間に延長
        クエリ数: 1クエリ/チーム
        """
        # 1週間前〜キックオフ（公式動画を拾いやすくするため期間延長）
        published_after = kickoff_time - timedelta(hours=self.TRAINING_SEARCH_HOURS)
        
        # 日本語クエリ + relevanceLanguage=ja
        query = f"{team_name} トレーニング"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=kickoff_time,
            max_results=self.FETCH_MAX_RESULTS,
            relevance_language="ja",
        )
        
        for v in videos:
            v["category"] = "training"
        
        # post-fetchフィルタ適用
        return self._apply_trusted_channel_filter(videos)
    
    def _deduplicate(self, videos: List[Dict]) -> List[Dict]:
        """重複を排除"""
        seen = set()
        unique = []
        for v in videos:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                unique.append(v)
        return unique
    
    def _get_key_players(self, match: MatchData) -> Tuple[List[str], List[str]]:
        """
        各チームのキープレイヤーを取得（FW/MF優先）
        
        デバッグモード: 1人/チーム
        通常モード: 3人/チーム
        """
        player_count = 1 if config.DEBUG_MODE else 3
        
        home_players = []
        away_players = []
        
        # ホームチーム - リストから取得（FW/MF優先は形式的）
        if match.home_lineup:
            # スタメンリストから後ろの方（FW想定）を優先
            for player in reversed(match.home_lineup):
                if len(home_players) < player_count:
                    home_players.append(player)
        
        # アウェイチーム
        if match.away_lineup:
            for player in reversed(match.away_lineup):
                if len(away_players) < player_count:
                    away_players.append(player)
        
        return home_players, away_players
    
    def get_videos_for_match(self, match: MatchData) -> List[Dict]:
        """試合に関連する動画を取得"""
        all_videos = []
        
        home_team = match.home_team
        away_team = match.away_team
        home_manager = getattr(match, 'home_manager', '')
        away_manager = getattr(match, 'away_manager', '')
        
        # kickoff_jstは "2025/12/21 00:00 JST" 形式の文字列
        # JSTとしてパースしてUTCに変換
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
        if home_manager:
            logger.info(f"Home manager: {home_manager}")
        if away_manager:
            logger.info(f"Away manager: {away_manager}")
        
        # キープレイヤーを取得
        home_players, away_players = self._get_key_players(match)
        logger.info(f"Key players - Home: {home_players}, Away: {away_players}")
        
        # 1. 記者会見（2クエリ = 1クエリ × 2チーム）
        all_videos.extend(self._search_press_conference(home_team, home_manager, kickoff_time))
        all_videos.extend(self._search_press_conference(away_team, away_manager, kickoff_time))
        
        # 2. 因縁（1クエリ）
        all_videos.extend(self._search_historic_clashes(home_team, away_team, kickoff_time))
        
        # 3. 戦術（2クエリ = 1クエリ × 2チーム）
        all_videos.extend(self._search_tactical(home_team, kickoff_time))
        all_videos.extend(self._search_tactical(away_team, kickoff_time))
        
        # 4. 選手紹介（6クエリ = 3選手 × 2チーム、デバッグモードは2クエリ）
        for player in home_players:
            all_videos.extend(self._search_player_highlight(player, kickoff_time))
        for player in away_players:
            all_videos.extend(self._search_player_highlight(player, kickoff_time))
        
        # 5. 練習風景（2クエリ = 1クエリ × 2チーム）
        all_videos.extend(self._search_training(home_team, kickoff_time))
        all_videos.extend(self._search_training(away_team, kickoff_time))
        
        # 重複排除
        unique_videos = self._deduplicate(all_videos)
        
        # 最終ソート（信頼チャンネル優先）
        unique_videos = self._apply_trusted_channel_filter(unique_videos)
        
        logger.info(f"Found {len(unique_videos)} unique videos for {home_team} vs {away_team}")
        
        return unique_videos
    
    def process_matches(self, matches: List[MatchData]) -> Dict[str, List[Dict]]:
        """全試合の動画を取得"""
        results = {}
        
        for match in matches:
            if match.is_target:
                match_key = f"{match.home_team} vs {match.away_team}"
                results[match_key] = self.get_videos_for_match(match)
        
        return results
