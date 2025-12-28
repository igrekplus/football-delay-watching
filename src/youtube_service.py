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
from typing import List, Dict, Optional, Tuple, Callable
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
from src.youtube_filter import YouTubePostFilter

logger = logging.getLogger(__name__)

# YouTube検索結果のキャッシュ設定
YOUTUBE_CACHE_DIR = Path("api_cache/youtube")
YOUTUBE_CACHE_TTL_HOURS = 168  # キャッシュ有効期限（1週間）


class YouTubeService:
    """YouTube動画を取得するサービス"""
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    # チューニング可能なパラメータ
    HISTORIC_SEARCH_DAYS = 730               # 過去ハイライト検索期間（2年）
    PRESS_CONFERENCE_SEARCH_HOURS = 48       # 記者会見検索期間（48時間）
    TRAINING_SEARCH_HOURS = 168              # 練習動画検索期間（1週間）
    TACTICAL_SEARCH_DAYS = 180               # 戦術動画検索期間（6ヶ月）
    PLAYER_SEARCH_DAYS = 180                 # 選手紹介動画検索期間（6ヶ月）
    
    # 全カテゴリ共通: 取得件数（フィルタ後に絞り込む）
    FETCH_MAX_RESULTS = 50
    
    def __init__(
        self,
        api_key: str = None,
        http_get: Optional[Callable] = None,
        search_override: Optional[Callable[[Dict], List[Dict]]] = None,
        cache_enabled: Optional[bool] = None,
    ):
        # YOUTUBE_API_KEY を優先、なければ GOOGLE_API_KEY にフォールバック
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or config.GOOGLE_API_KEY
        self._channel_id_cache: Dict[str, str] = {}
        self._http_get = http_get or requests.get
        self._search_override = search_override
        # allow forcing cache behavior for healthcheck/mocks
        self._cache_enabled = config.USE_API_CACHE if cache_enabled is None else cache_enabled
        
        # フィルターインスタンス
        self.filter = YouTubePostFilter()
        
        # API呼び出しカウンター
        self.api_call_count = 0
        self.cache_hit_count = 0
    
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
        if not self._cache_enabled:
            return None
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
            self.cache_hit_count += 1
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"Failed to read YouTube cache: {e}")
            return None
    
    def _write_cache(self, cache_key: str, results: List[Dict]):
        """キャッシュに書き込み"""
        if not self._cache_enabled:
            return
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
        region_code: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        YouTube検索を実行（1週間キャッシュ付き）
        
        post-fetch方式: チャンネル指定なしで検索し、後からフィルタ
        
        Args:
            relevance_language: 結果の言語優先度（ISO 639-1、例: "ja"）
        """
        
        # モック/テスト用の上書きがある場合はここで返す
        if self._search_override:
            try:
                return self._search_override({
                    "query": query,
                    "published_after": published_after,
                    "published_before": published_before,
                    "max_results": max_results,
                    "relevance_language": relevance_language,
                    "region_code": region_code,
                    "channel_id": channel_id,
                })[:max_results]
            except Exception as e:
                logger.warning(f"YouTube search override failed: {e}")
                return []

        # キャッシュチェック（チャンネルIDなしで検索するため、channel_id=None）
        # relevance_language/region_codeもキャッシュキーに含める
        cache_key = self._get_cache_key(
            query + (relevance_language or "") + (region_code or ""),
            channel_id,
            published_after,
            published_before,
        )
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
            if region_code:
                params["regionCode"] = region_code
            if channel_id:
                params["channelId"] = channel_id
            
            response = self._http_get(url, params=params)
            
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
                            "description": item["snippet"].get("description", ""),
                            "original_index": i,  # relevance順を保持
                        })
                
                # キャッシュ保存
                self._write_cache(cache_key, results)
                self.api_call_count += 1
                logger.info(f"YouTube API: '{query}' -> {len(results)} results (API calls: {self.api_call_count})")
                
                return results
            else:
                logger.warning(f"YouTube search failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        
        return []

    def search_videos_raw(
        self,
        query: str,
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None,
        max_results: int = 10,
        relevance_language: Optional[str] = None,
        region_code: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> List[Dict]:
        """healthcheck等から使うための生検索API"""
        return self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=max_results,
            relevance_language=relevance_language,
            region_code=region_code,
            channel_id=channel_id,
        )
    
    def _apply_trusted_channel_filter(self, videos: List[Dict]) -> List[Dict]:
        """
        信頼チャンネル優先でソート + バッジ付与
        
        後方互換性のため残す（内部ではself.filter.sort_trustedを使用）
        """
        return self.filter.sort_trusted(videos)

    def apply_trusted_channel_sort(self, videos: List[Dict]) -> List[Dict]:
        """healthcheck等から使うための信頼チャンネル優先ソート（公開API）"""
        return self.filter.sort_trusted(videos)

    def apply_player_post_filter(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        選手紹介向けのpost-filter（公開API）
        
        後方互換性のため残す（内部ではself.filter.exclude_highlightsを使用）
        """
        return self.filter.exclude_highlights(videos)

    # ========== 公開API（healthcheck等から使用） ==========
    
    def search_training_videos(
        self,
        team_name: str,
        kickoff_time: datetime,
        max_results: int = 10,
    ) -> List[Dict]:
        """
        練習動画を検索（公開API）
        
        ヘルスチェックやデバッグ用に本体ロジックを公開
        """
        videos = self._search_training(team_name, kickoff_time)
        return videos[:max_results]
    
    def search_player_videos(
        self,
        player_name: str,
        team_name: str,
        kickoff_time: datetime,
        max_results: int = 10,
        apply_post_filter: bool = True,
    ) -> Dict[str, List[Dict]]:
        """
        選手紹介動画を検索（公開API）
        
        Returns:
            apply_post_filter=True の場合: {"kept": [...], "removed": [...]}
            apply_post_filter=False の場合: {"kept": [...], "removed": []}
        """
        videos = self._search_player_highlight(player_name, team_name, kickoff_time)
        
        if apply_post_filter:
            filtered = self.apply_player_post_filter(videos)
            filtered["kept"] = filtered["kept"][:max_results]
            return filtered
        else:
            return {"kept": videos[:max_results], "removed": []}
    
    def _search_press_conference(
        self,
        team_name: str,
        manager_name: str,
        kickoff_time: datetime,
    ) -> Dict[str, List[Dict]]:
        """
        記者会見を検索
        
        Returns:
            {"kept": [...], "removed": [...], "overflow": [...]}
        """
        # 48時間前〜キックオフ
        published_after = kickoff_time - timedelta(hours=self.PRESS_CONFERENCE_SEARCH_HOURS)
        
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
            v["query_label"] = manager_name or team_name
        
        # フィルター適用（press_conferenceは除外）
        filter_result = self.filter.apply_filters(videos, [
            "match_highlights", "highlights", "full_match", "live_stream", "reaction"
        ])
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        return {"kept": kept, "removed": removed}
    
    def _search_historic_clashes(
        self,
        home_team: str,
        away_team: str,
        kickoff_time: datetime,
    ) -> Dict[str, List[Dict]]:
        """
        過去の名勝負・対戦ハイライトを検索
        
        Returns:
            {"kept": [...], "removed": [...], "overflow": [...]}
        """
        # 過去2年〜キックオフ24時間前までの動画を検索（ネタバレ防止）
        published_after = kickoff_time - timedelta(days=self.HISTORIC_SEARCH_DAYS)
        published_before = kickoff_time - timedelta(hours=24)
        
        query = f"{home_team} vs {away_team} highlights"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = "historic"
        
        # フィルター適用（highlightsは除外、live/press_conference/reactionは除外）
        filter_result = self.filter.apply_filters(videos, [
            "live_stream", "press_conference", "reaction"
        ])
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        return {"kept": kept, "removed": []}
    
    def _search_tactical(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> Dict[str, List[Dict]]:
        """
        戦術分析を検索
        
        Returns:
            {"kept": [...], "removed": [...], "overflow": [...]}
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
            v["query_label"] = team_name
        
        # フィルター適用
        filter_result = self.filter.apply_filters(videos, [
            "match_highlights", "highlights", "full_match", "live_stream", "press_conference", "reaction"
        ])
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        return {"kept": kept, "removed": removed}
    
    def _search_player_highlight(
        self,
        player_name: str,
        team_name: str,
        kickoff_time: datetime,
    ) -> Dict[str, List[Dict]]:
        """
        選手紹介動画を検索
        
        Returns:
            {"kept": [...], "removed": [...], "overflow": [...]}
        """
        published_after = kickoff_time - timedelta(days=self.PLAYER_SEARCH_DAYS)
        
        # 英語名 + カタカナの「プレー」で検索
        if team_name:
            query = f"{player_name} {team_name} プレー"
        else:
            query = f"{player_name} プレー"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=kickoff_time,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = "player_highlight"
            v["query_label"] = player_name
        
        # フィルター適用
        filter_result = self.filter.apply_filters(videos, [
            "match_highlights", "highlights", "full_match", "live_stream", "press_conference", "reaction"
        ])
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        return {"kept": kept, "removed": removed}
    
    def _search_training(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> Dict[str, List[Dict]]:
        """
        練習風景を検索
        
        Returns:
            {"kept": [...], "removed": [...], "overflow": [...]}
        """
        # 1週間前〜キックオフ
        published_after = kickoff_time - timedelta(hours=self.TRAINING_SEARCH_HOURS)
        
        # 英語クエリ（training）
        query = f"{team_name} training"
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=kickoff_time,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = "training"
            v["query_label"] = team_name
        
        # フィルター適用
        filter_result = self.filter.apply_filters(videos, [
            "match_highlights", "highlights", "full_match", "live_stream", "press_conference", "reaction"
        ])
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        return {"kept": kept, "removed": removed}
    
    def _deduplicate(self, videos: List[Dict]) -> List[Dict]:
        """重複を排除（後方互換性のため、内部ではself.filter.deduplicateを使用）"""
        return self.filter.deduplicate(videos)
    
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
    
    def get_videos_for_match(self, match: MatchData) -> Dict[str, List[Dict]]:
        """試合に関連する動画を取得（kept/removed/overflowを含む辞書を返す）"""
        all_kept = []
        all_removed = []
        all_overflow = []
        
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
        
        # ヘルパー: 結果をマージ
        def merge_result(result: Dict[str, List[Dict]]):
            all_kept.extend(result.get("kept", []))
            all_removed.extend(result.get("removed", []))
            all_overflow.extend(result.get("overflow", []))
        
        # 1. 記者会見（2クエリ = 1クエリ × 2チーム）
        merge_result(self._search_press_conference(home_team, home_manager, kickoff_time))
        merge_result(self._search_press_conference(away_team, away_manager, kickoff_time))
        
        # 2. 因縁（1クエリ）
        merge_result(self._search_historic_clashes(home_team, away_team, kickoff_time))
        
        # 3. 戦術（2クエリ = 1クエリ × 2チーム）
        merge_result(self._search_tactical(home_team, kickoff_time))
        merge_result(self._search_tactical(away_team, kickoff_time))
        
        # 4. 選手紹介（各選手×チーム、デバッグモードは1人/チーム）
        for player in home_players:
            merge_result(self._search_player_highlight(player, home_team, kickoff_time))
        for player in away_players:
            merge_result(self._search_player_highlight(player, away_team, kickoff_time))
        
        # 5. 練習風景（2クエリ = 1クエリ × 2チーム）
        merge_result(self._search_training(home_team, kickoff_time))
        merge_result(self._search_training(away_team, kickoff_time))
        
        # 重複排除（keptのみ）
        unique_kept = self.filter.deduplicate(all_kept)
        
        # カテゴリ別にグルーピングして10件制限
        MAX_PER_CATEGORY = 10
        categories = ["press_conference", "historic", "tactical", "player_highlight", "training"]
        final_kept = []
        final_overflow = []
        
        for category in categories:
            cat_videos = [v for v in unique_kept if v.get("category") == category]
            if cat_videos:
                # 既にsort_trusted済みだが、2チーム分をまとめた後なので再ソート
                cat_videos = self.filter.sort_trusted(cat_videos)
                final_kept.extend(cat_videos[:MAX_PER_CATEGORY])
                if len(cat_videos) > MAX_PER_CATEGORY:
                    final_overflow.extend(cat_videos[MAX_PER_CATEGORY:])
        
        logger.info(f"Found {len(final_kept)} kept, {len(all_removed)} removed, {len(final_overflow)} overflow videos for {home_team} vs {away_team}")
        
        return {
            "kept": final_kept,
            "removed": all_removed,
            "overflow": final_overflow
        }
    
    def process_matches(self, matches: List[MatchData]) -> Dict[str, List[Dict]]:
        """全試合の動画を取得"""
        # モックモード: APIアクセスなしでリアルなダミーデータを返却
        if config.USE_MOCK_DATA:
            return self._get_mock_videos(matches)
        
        results = {}
        
        for match in matches:
            if match.is_target:
                match_key = f"{match.home_team} vs {match.away_team}"
                results[match_key] = self.get_videos_for_match(match)
        
        return results
    
    def _get_mock_videos(self, matches: List[MatchData]) -> Dict[str, List[Dict]]:
        """モック用YouTube動画データ（MC vs West Ham 2025-12-21 実データベース）"""
        results = {}
        
        for match in matches:
            if not match.is_target:
                continue
            match_key = f"{match.home_team} vs {match.away_team}"
            
            # リアルなモックデータ（実際のYouTubeキャッシュから構成）
            results[match_key] = [
                # 記者会見
                {"video_id": "FYuyWxcX604", "title": "Manager's Preview | Pep Guardiola press conference", 
                 "url": "https://www.youtube.com/watch?v=FYuyWxcX604", "channel_id": "UCkzCjdRMrW2vXLx8mvPVLdQ",
                 "channel_name": "Man City", "thumbnail_url": "https://i.ytimg.com/vi/FYuyWxcX604/mqdefault.jpg",
                 "published_at": "2025-12-19T14:00:00Z", "description": "Pep Guardiola speaks ahead of...",
                 "category": "press_conference", "is_trusted": True, "channel_display": "✅ Man City"},
                {"video_id": "qmsEeXaoBu8", "title": "Pep Guardiola Speaks On His Future At Man City",
                 "url": "https://www.youtube.com/watch?v=qmsEeXaoBu8", "channel_id": "UC7gFIlP3YVcY5gYhPdQ0jNA",
                 "channel_name": "DAZN Football", "thumbnail_url": "https://i.ytimg.com/vi/qmsEeXaoBu8/mqdefault.jpg",
                 "published_at": "2025-12-19T16:30:00Z", "description": "Exclusive interview with Pep...",
                 "category": "press_conference", "is_trusted": True, "channel_display": "✅ DAZN Football"},
                # 因縁（過去ハイライト）
                {"video_id": "sAewmh-Lu8U", "title": "EXTENDED HIGHLIGHTS | 4-IN-A-ROW | Man City 3-1 West Ham",
                 "url": "https://www.youtube.com/watch?v=sAewmh-Lu8U", "channel_id": "UCkzCjdRMrW2vXLx8mvPVLdQ",
                 "channel_name": "Man City", "thumbnail_url": "https://i.ytimg.com/vi/sAewmh-Lu8U/mqdefault.jpg",
                 "published_at": "2024-05-19T22:00:00Z", "description": "City secure fourth consecutive title...",
                 "category": "historic", "is_trusted": True, "channel_display": "✅ Man City"},
                {"video_id": "rPmUSbkSl34", "title": "Man City Win The Premier League! | Man City 3-1 West Ham",
                 "url": "https://www.youtube.com/watch?v=rPmUSbkSl34", "channel_id": "UCG5qGW...",
                 "channel_name": "Premier League", "thumbnail_url": "https://i.ytimg.com/vi/rPmUSbkSl34/mqdefault.jpg",
                 "published_at": "2024-05-19T23:00:00Z", "description": "Premier League champions crowned...",
                 "category": "historic", "is_trusted": True, "channel_display": "✅ Premier League"},
                # 戦術分析
                {"video_id": "B6RgCAiLg44", "title": "【試合総括】マンチェスターCvsナポリを解説！",
                 "url": "https://www.youtube.com/watch?v=B6RgCAiLg44", "channel_id": "UCxxxxx",
                 "channel_name": "GOAT理論【切り抜き】", "thumbnail_url": "https://i.ytimg.com/vi/B6RgCAiLg44/mqdefault.jpg",
                 "published_at": "2025-12-10T10:00:00Z", "description": "ナポリの守備を攻略したペップの戦略...",
                 "category": "tactical", "is_trusted": False, "channel_display": "⚠️ GOAT理論【切り抜き】"},
                # 選手紹介
                {"video_id": "VPgwGN9kGpI", "title": "Erling Haaland's First 100 Premier League Goals!",
                 "url": "https://www.youtube.com/watch?v=VPgwGN9kGpI", "channel_id": "UCG5qGW...",
                 "channel_name": "Premier League", "thumbnail_url": "https://i.ytimg.com/vi/VPgwGN9kGpI/mqdefault.jpg",
                 "published_at": "2025-11-30T15:00:00Z", "description": "Watch all 100 of Haaland's goals...",
                 "category": "player_highlight", "is_trusted": True, "channel_display": "✅ Premier League"},
                # 練習風景
                {"video_id": "Hv2IXyyAgBQ", "title": "HIGHLIGHTS! Haaland and Foden help power City to victory",
                 "url": "https://www.youtube.com/watch?v=Hv2IXyyAgBQ", "channel_id": "UCkzCjdRMrW2vXLx8mvPVLdQ",
                 "channel_name": "Man City", "thumbnail_url": "https://i.ytimg.com/vi/Hv2IXyyAgBQ/mqdefault.jpg",
                 "published_at": "2025-12-14T22:00:00Z", "description": "Crystal Palace 0-3 Man City...",
                 "category": "training", "is_trusted": True, "channel_display": "✅ Man City"},
            ]
            logger.info(f"[MOCK] YouTube: Returning {len(results[match_key])} mock videos for {match_key}")
        
        return results
