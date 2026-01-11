"""
YouTube動画取得サービス

試合前の関連動画（記者会見、過去の名勝負、戦術解説、練習風景、選手紹介）を
YouTube Data API v3で取得する。

Issue #27: クエリ削減（20→13/試合）とpost-fetchフィルタ方式への移行
Issue #102:検索/キャッシュはYouTubeSearchClientに統一
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Callable

from config import config
from settings.channels import (
    get_team_channel,
    is_trusted_channel,
    get_channel_info,
    TACTICS_CHANNELS,
)
from settings.search_specs import (
    YOUTUBE_SEARCH_SPECS,
    build_youtube_query,
    get_youtube_time_window,
    get_youtube_exclude_filters,
)
from src.domain.models import MatchAggregate
from src.youtube_filter import YouTubePostFilter
from src.clients.youtube_client import YouTubeSearchClient

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube動画を取得するサービス"""
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    # 検索パラメータは settings/search_specs.py で管理
    # 全カテゴリ共通: 取得件数（フィルタ後に絞り込む）
    FETCH_MAX_RESULTS = 50
    
    def __init__(
        self,
        api_key: str = None,
        http_get: Optional[Callable] = None,
        search_override: Optional[Callable[[Dict], List[Dict]]] = None,
        cache_enabled: Optional[bool] = None,
        youtube_client: Optional[YouTubeSearchClient] = None,
    ):
        # モック/テスト用の上書き関数
        self._search_override = search_override
        
        # Issue #107: search_override呼び出し回数
        self._override_call_count = 0
        
        # キャッシュ設定（clientに渡す）
        effective_cache_enabled = config.USE_API_CACHE if cache_enabled is None else cache_enabled
        
        # YouTubeSearchClient（DI or 自動生成）
        # Issue #102: 検索/キャッシュはClientに統一
        if youtube_client is not None:
            self._youtube_client = youtube_client
        else:
            self._youtube_client = YouTubeSearchClient(
                api_key=api_key,
                http_get=http_get,
                cache_enabled=effective_cache_enabled,
            )
        
        # フィルターインスタンス
        self.filter = YouTubePostFilter()
    
    # ========== 統計プロパティ（後方互換性のため維持） ==========
    
    @property
    def api_call_count(self) -> int:
        """API呼び出し回数（YouTubeSearchClientから取得）"""
        return self._youtube_client.api_call_count
    
    @property
    def cache_hit_count(self) -> int:
        """キャッシュヒット回数（YouTubeSearchClientから取得）"""
        return self._youtube_client.cache_hit_count
    
    @property
    def override_call_count(self) -> int:
        """search_override呼び出し回数（Issue #107）"""
        return self._override_call_count
    
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
        YouTube検索を実行（YouTubeSearchClient経由、1週間キャッシュ付き）
        
        post-fetch方式: チャンネル指定なしで検索し、後からフィルタ
        
        Args:
            relevance_language: 結果の言語優先度（ISO 639-1、例: "ja"）
        """
        # モック/テスト用の上書きがある場合はここで返す（Issue #107: 統計も更新）
        if self._search_override:
            try:
                self._override_call_count += 1
                result = self._search_override({
                    "query": query,
                    "published_after": published_after,
                    "published_before": published_before,
                    "max_results": max_results,
                    "relevance_language": relevance_language,
                    "region_code": region_code,
                    "channel_id": channel_id,
                })[:max_results]
                logger.info(f"YouTube [OVERRIDE]: '{query}' -> {len(result)} results (override calls: {self._override_call_count})")
                return result
            except Exception as e:
                logger.warning(f"YouTube search override failed: {e}")
                return []
        
        # Issue #102: YouTubeSearchClient経由で検索（キャッシュ/API統一）
        return self._youtube_client.search(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=max_results,
            relevance_language=relevance_language,
            region_code=region_code,
            channel_id=channel_id,
        )

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
        category = "press_conference"
        
        # スペックから時間ウィンドウを取得
        published_after, published_before = get_youtube_time_window(category, kickoff_time)
        
        # スペックからクエリを生成
        query = build_youtube_query(category, team_name=team_name, manager_name=manager_name)
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = category
            v["query_label"] = manager_name or team_name
        
        # スペックからフィルタを取得して適用
        exclude_filters = get_youtube_exclude_filters(category)
        filter_result = self.filter.apply_filters(videos, exclude_filters)
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
        category = "historic"
        
        # スペックから時間ウィンドウを取得
        published_after, published_before = get_youtube_time_window(category, kickoff_time)
        
        # スペックからクエリを生成
        query = build_youtube_query(category, home_team=home_team, away_team=away_team)
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = category
        
        # スペックからフィルタを取得して適用
        exclude_filters = get_youtube_exclude_filters(category)
        filter_result = self.filter.apply_filters(videos, exclude_filters)
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        # Issue #109: LLM Post-Filter（Gemini）を適用
        # モック/オーバーライドモードではスキップ
        if kept and not self._search_override and not config.USE_MOCK_DATA:
            try:
                from src.clients.gemini_rest_client import GeminiRestClient
                gemini_client = GeminiRestClient()
                llm_result = self.filter.filter_by_context(kept, home_team, away_team, gemini_client)
                removed.extend(llm_result["removed"])
                kept = llm_result["kept"]
            except Exception as e:
                logger.warning(f"LLM filter skipped due to error: {e}")
        
        return {"kept": kept, "removed": removed}
    
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
        category = "tactical"
        
        # スペックから時間ウィンドウを取得
        published_after, published_before = get_youtube_time_window(category, kickoff_time)
        
        # スペックからクエリを生成
        query = build_youtube_query(category, team_name=team_name)
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = category
            v["query_label"] = team_name
        
        # スペックからフィルタを取得して適用
        exclude_filters = get_youtube_exclude_filters(category)
        filter_result = self.filter.apply_filters(videos, exclude_filters)
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
        category = "player_highlight"
        
        # スペックから時間ウィンドウを取得
        published_after, published_before = get_youtube_time_window(category, kickoff_time)
        
        # スペックからクエリを生成
        query = build_youtube_query(category, player_name=player_name, team_name=team_name)
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = category
            v["query_label"] = player_name
        
        # スペックからフィルタを取得して適用
        exclude_filters = get_youtube_exclude_filters(category)
        filter_result = self.filter.apply_filters(videos, exclude_filters)
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
        category = "training"
        
        # スペックから時間ウィンドウを取得
        published_after, published_before = get_youtube_time_window(category, kickoff_time)
        
        # スペックからクエリを生成
        query = build_youtube_query(category, team_name=team_name)
        
        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        
        for v in videos:
            v["category"] = category
            v["query_label"] = team_name
        
        # スペックからフィルタを取得して適用
        exclude_filters = get_youtube_exclude_filters(category)
        filter_result = self.filter.apply_filters(videos, exclude_filters)
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # sort_trusted適用（件数制限なし）
        kept = self.filter.sort_trusted(kept)
        
        return {"kept": kept, "removed": removed}
    
    def _deduplicate(self, videos: List[Dict]) -> List[Dict]:
        """重複を排除（後方互換性のため、内部ではself.filter.deduplicateを使用）"""
        return self.filter.deduplicate(videos)
    
    def _get_key_players(self, match: MatchAggregate) -> Tuple[List[str], List[str]]:
        """
        各チームのキープレイヤーを取得（FW/MF優先）
        
        デバッグモード: 1人/チーム
        通常モード: 3人/チーム
        """
        player_count = 1 if config.DEBUG_MODE else 3
        
        home_players = []
        away_players = []
        
        # ホームチーム - リストから取得（FW/MF優先は形式的）
        if match.facts.home_lineup:
            # スタメンリストから後ろの方（FW想定）を優先
            for player in reversed(match.facts.home_lineup):
                if len(home_players) < player_count:
                    home_players.append(player)
        
        # アウェイチーム
        if match.facts.away_lineup:
            for player in reversed(match.facts.away_lineup):
                if len(away_players) < player_count:
                    away_players.append(player)
        
        return home_players, away_players
    
    def get_videos_for_match(self, match: MatchAggregate) -> Dict[str, List[Dict]]:
        """試合に関連する動画を取得（kept/removed/overflowを含む辞書を返す）"""
        all_kept = []
        all_removed = []
        all_overflow = []
        
        home_team = match.core.home_team
        away_team = match.core.away_team
        home_manager = match.facts.home_manager
        away_manager = match.facts.away_manager
        
        # Issue #70: kickoff_at_utc を優先使用
        import pytz
        from src.utils.datetime_util import DateTimeUtil
        
        if match.core.kickoff_at_utc is not None:
            kickoff_time = match.core.kickoff_at_utc
            logger.info(f"Kickoff time (from kickoff_at_utc): {kickoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        else:
            # フォールバック: kickoff_jst 文字列をパース
            kickoff_time = DateTimeUtil.parse_kickoff_jst(match.core.kickoff_jst)
            if kickoff_time:
                logger.info(f"Kickoff time (parsed from kickoff_jst): {match.core.kickoff_jst} -> UTC: {kickoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            else:
                logger.warning(f"Failed to parse kickoff_jst: {match.core.kickoff_jst}, using current time")
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
    
    def process_matches(self, matches: List[MatchAggregate]) -> Dict[str, List[Dict]]:
        """全試合の動画を取得"""
        # モックモード: APIアクセスなしでリアルなダミーデータを返却
        if config.USE_MOCK_DATA:
            return self._get_mock_videos(matches)
        
        results = {}
        
        for match in matches:
            if match.core.is_target:
                # Issue #163: S/Aランクの試合のみ動画検索を実行（クォータ最適化）
                if match.core.rank not in ["S", "A", "Absolute"]:
                    logger.info(f"Skipping YouTube search for low-rank match: {match.core.home_team} vs {match.core.away_team} (rank={match.core.rank})")
                    continue
                match_key = f"{match.core.home_team} vs {match.core.away_team}"
                results[match_key] = self.get_videos_for_match(match)
        
        return results
    
    def _get_mock_videos(self, matches: List[MatchAggregate]) -> Dict[str, List[Dict]]:
        """モック用YouTube動画データを取得"""
        from src.mock_provider import MockProvider
        return MockProvider.get_youtube_videos_for_matches(matches)

