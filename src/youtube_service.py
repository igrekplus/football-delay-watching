"""
YouTube動画取得サービス

試合前の関連動画（記者会見、過去の名勝負、戦術解説、練習風景、選手紹介）を
YouTube Data API v3で取得する。

Issue #27: クエリ削減（20→13/試合）とpost-fetchフィルタ方式への移行
Issue #102:検索/キャッシュはYouTubeSearchClientに統一
"""

import logging
from collections.abc import Callable
from datetime import datetime

from config import config
from settings.channels import (
    find_team_channel_ids,
    get_channel_info,
    get_channels_by_categories,
    get_team_name_variants,
)
from settings.search_specs import (
    build_youtube_query,
    get_youtube_allowed_channel_categories,
    get_youtube_max_display,
    get_youtube_time_window,
)
from src.clients.http_client import HttpClient
from src.clients.youtube_client import YouTubeSearchClient
from src.domain.models import MatchAggregate
from src.youtube_filter import YouTubePostFilter

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
        http_client: HttpClient | None = None,
        search_override: Callable[[dict], list[dict]] | None = None,
        cache_enabled: bool | None = None,
        youtube_client: YouTubeSearchClient | None = None,
    ):
        # モック/テスト用の上書き関数
        self._search_override = search_override

        # Issue #107: search_override呼び出し回数
        self._override_call_count = 0

        # キャッシュ設定（clientに渡す）
        effective_cache_enabled = (
            config.USE_API_CACHE if cache_enabled is None else cache_enabled
        )

        # YouTubeSearchClient（DI or 自動生成）
        # Issue #102: 検索/キャッシュはClientに統一
        if youtube_client is not None:
            self._youtube_client = youtube_client
        else:
            self._youtube_client = YouTubeSearchClient(
                api_key=api_key,
                http_client=http_client,
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
        published_after: datetime | None = None,
        published_before: datetime | None = None,
        max_results: int = 10,
        relevance_language: str | None = None,
        region_code: str | None = None,
        channel_id: str | None = None,
    ) -> list[dict]:
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
                result = self._search_override(
                    {
                        "query": query,
                        "published_after": published_after,
                        "published_before": published_before,
                        "max_results": max_results,
                        "relevance_language": relevance_language,
                        "region_code": region_code,
                        "channel_id": channel_id,
                    }
                )[:max_results]
                logger.info(
                    f"YouTube [OVERRIDE]: '{query}' -> {len(result)} results (override calls: {self._override_call_count})"
                )
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
        published_after: datetime | None = None,
        published_before: datetime | None = None,
        max_results: int = 10,
        relevance_language: str | None = None,
        region_code: str | None = None,
        channel_id: str | None = None,
    ) -> list[dict]:
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

    # ========== playlist方式の共通取得ロジック ==========

    # UNEXT チャンネルID（playlistItems で確実に取得できる）
    UNEXT_CHANNEL_ID = "UCMjvvElkdLRTgcTKklAUkSw"

    def _fetch_from_playlists(
        self,
        channel_ids: list[str],
        published_after: datetime | None,
        published_before: datetime | None,
        title_keywords: list[str],
        category: str,
        require_all_keywords: bool = False,
    ) -> list[dict]:
        """
        複数チャンネルのuploadsプレイリストから動画を取得・フィルタ

        Args:
            channel_ids: 対象チャンネルIDリスト
            published_after / published_before: 日付範囲
            title_keywords: タイトルに含まれるべきキーワード（OR条件、require_all_keywords=True でAND）
            category: 動画カテゴリ
            require_all_keywords: Trueならキーワードを全て含む動画のみ残す
        """
        results = []
        seen_ids = set()

        for channel_id in channel_ids:
            videos = self._youtube_client.get_channel_playlist_videos(
                channel_id=channel_id,
                max_results=50,
                published_after=published_after,
                published_before=published_before,
            )
            for v in videos:
                vid_id = v.get("video_id", "")
                if vid_id in seen_ids:
                    continue
                title = v.get("title", "").lower()
                if title_keywords:
                    if require_all_keywords:
                        if not all(kw.lower() in title for kw in title_keywords):
                            continue
                    else:
                        if not any(kw.lower() in title for kw in title_keywords):
                            continue
                seen_ids.add(vid_id)
                v["category"] = category
                info = get_channel_info(v.get("channel_id", channel_id))
                v["is_trusted"] = True
                v["channel_display"] = f"✅ {info['name']}"
                results.append(v)

        return results

    def _apply_trusted_channel_filter(self, videos: list[dict]) -> list[dict]:
        """
        信頼チャンネル優先でソート + バッジ付与

        後方互換性のため残す（内部ではself.filter.sort_trustedを使用）
        """
        return self.filter.sort_trusted(videos)

    def apply_trusted_channel_sort(self, videos: list[dict]) -> list[dict]:
        """healthcheck等から使うための信頼チャンネル優先ソート（公開API）"""
        return self.filter.sort_trusted(videos)

    def apply_player_post_filter(self, videos: list[dict]) -> dict[str, list[dict]]:
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
    ) -> list[dict]:
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
    ) -> dict[str, list[dict]]:
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
    ) -> dict[str, list[dict]]:
        """
        記者会見を検索（playlist方式: チーム公式チャンネルのみ）

        Returns:
            {"kept": [...], "removed": [...]}
        """
        category = "press_conference"
        published_after, published_before = get_youtube_time_window(category, kickoff_time)

        # チーム名に対応するチャンネルIDを取得
        channel_ids = find_team_channel_ids(team_name)
        if not channel_ids:
            logger.info(f"No team channel found for '{team_name}', skipping press_conference")
            return {"kept": [], "removed": []}

        # タイトルキーワード: "press conference" or "記者会見"
        keywords = ["press conference", "記者会見"]
        if manager_name:
            keywords.append(manager_name)

        kept = self._fetch_from_playlists(
            channel_ids=channel_ids,
            published_after=published_after,
            published_before=published_before,
            title_keywords=keywords,
            category=category,
        )
        for v in kept:
            v["query_label"] = manager_name or team_name

        return {"kept": kept, "removed": []}

    def _search_historic_clashes(
        self,
        home_team: str,
        away_team: str,
        kickoff_time: datetime,
    ) -> dict[str, list[dict]]:
        """
        過去の名勝負・対戦ハイライトを検索（search.list + 厳格チャンネルフィルタ）

        1年さかのぼるため playlist の50件制限では不足。search.list でキーワード+日付検索後、
        許可チャンネルカテゴリ（team/league/broadcaster）のみ残す。

        Returns:
            {"kept": [...], "removed": [...]}
        """
        category = "historic"
        published_after, published_before = get_youtube_time_window(category, kickoff_time)
        query = build_youtube_query(category, home_team=home_team, away_team=away_team)

        videos = self._search_videos(
            query=query,
            published_after=published_after,
            published_before=published_before,
            max_results=self.FETCH_MAX_RESULTS,
        )
        for v in videos:
            v["category"] = category

        # 許可カテゴリかつ両チーム名のいずれかがタイトルに含まれるもののみ残す
        allowed_cats = get_youtube_allowed_channel_categories(category)
        from settings.channels import get_channel_info as _get_info

        home_variants = get_team_name_variants(home_team)
        away_variants = get_team_name_variants(away_team)

        kept = []
        removed = []
        for v in videos:
            info = _get_info(v.get("channel_id", ""))
            title_lower = v.get("title", "").lower()
            channel_ok = info["category"] in allowed_cats
            # 両チーム名が両方含まれる動画のみ（対戦を示すタイトル）
            home_ok = any(kw.lower() in title_lower for kw in home_variants)
            away_ok = any(kw.lower() in title_lower for kw in away_variants)
            title_ok = home_ok and away_ok
            if channel_ok and title_ok:
                v["is_trusted"] = True
                v["channel_display"] = f"✅ {info['name']}"
                kept.append(v)
            else:
                removed.append(v)

        logger.info(
            f"Historic filter: {len(kept)} kept, {len(removed)} removed "
            f"(allowed: {allowed_cats})"
        )
        return {"kept": kept, "removed": removed}

    def _search_tactical(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> dict[str, list[dict]]:
        """
        戦術分析を検索（playlist方式: tactics + media チャンネルのみ）

        Returns:
            {"kept": [...], "removed": [...]}
        """
        category = "tactical"
        published_after, published_before = get_youtube_time_window(category, kickoff_time)

        allowed_cats = get_youtube_allowed_channel_categories(category)
        channel_ids = get_channels_by_categories(allowed_cats)

        team_variants = get_team_name_variants(team_name)

        kept = self._fetch_from_playlists(
            channel_ids=channel_ids,
            published_after=published_after,
            published_before=published_before,
            title_keywords=team_variants,
            category=category,
        )
        for v in kept:
            v["query_label"] = team_name

        return {"kept": kept, "removed": []}

    def _search_player_highlight(
        self,
        player_name: str,
        team_name: str,
        kickoff_time: datetime,
    ) -> dict[str, list[dict]]:
        """
        選手紹介動画を検索（playlist方式: UNEXT・チーム公式・リーグ公式）

        Returns:
            {"kept": [...], "removed": [...]}
        """
        category = "player_highlight"
        published_after, published_before = get_youtube_time_window(category, kickoff_time)

        # 選手紹介はチーム固有チャンネル + UNEXT のみ（全broadcaster巡回は無駄が多い）
        channel_ids = find_team_channel_ids(team_name)
        if self.UNEXT_CHANNEL_ID not in channel_ids:
            channel_ids = [self.UNEXT_CHANNEL_ID] + channel_ids

        # フルネームに加え姓（ラストネーム）でもマッチ（例: "Erling Haaland" → "Haaland"）
        last_name = player_name.split()[-1]
        keywords = [player_name] if last_name == player_name else [player_name, last_name]

        kept = self._fetch_from_playlists(
            channel_ids=channel_ids,
            published_after=published_after,
            published_before=published_before,
            title_keywords=keywords,
            category=category,
        )
        for v in kept:
            v["query_label"] = player_name

        return {"kept": kept, "removed": []}

    def _deduplicate(self, videos: list[dict]) -> list[dict]:
        """重複を排除（後方互換性のため、内部ではself.filter.deduplicateを使用）"""
        return self.filter.deduplicate(videos)

    def _get_key_players(self, match: MatchAggregate) -> tuple[list[str], list[str]]:
        """
        各チームのキープレイヤーを取得（FW/MF優先）

        デバッグモード: 1人/チーム
        通常モード: 3人/チーム
        """
        player_count = 2 if config.DEBUG_MODE else 3

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

    def get_videos_for_match(self, match: MatchAggregate) -> dict[str, list[dict]]:
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
            logger.info(
                f"Kickoff time (from kickoff_at_utc): {kickoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            )
        else:
            # フォールバック: kickoff_jst 文字列をパース
            kickoff_time = DateTimeUtil.parse_kickoff_jst(match.core.kickoff_jst)
            if kickoff_time:
                logger.info(
                    f"Kickoff time (parsed from kickoff_jst): {match.core.kickoff_jst} -> UTC: {kickoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                )
            else:
                logger.warning(
                    f"Failed to parse kickoff_jst: {match.core.kickoff_jst}, using current time"
                )
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
        def merge_result(result: dict[str, list[dict]]):
            all_kept.extend(result.get("kept", []))
            all_removed.extend(result.get("removed", []))
            all_overflow.extend(result.get("overflow", []))

        # 1. 記者会見（各チームのチャンネルから取得）
        merge_result(
            self._search_press_conference(home_team, home_manager, kickoff_time)
        )
        merge_result(
            self._search_press_conference(away_team, away_manager, kickoff_time)
        )

        # 2. 過去の対戦（UNEXT・チーム・リーグ・放送局から取得）
        merge_result(self._search_historic_clashes(home_team, away_team, kickoff_time))

        # 3. 戦術（tactics・mediaチャンネルから取得）
        merge_result(self._search_tactical(home_team, kickoff_time))
        merge_result(self._search_tactical(away_team, kickoff_time))

        # 4. 選手紹介（UNEXT・チーム・リーグから取得、デバッグモードは1人/チーム）
        for player in home_players:
            merge_result(self._search_player_highlight(player, home_team, kickoff_time))
        for player in away_players:
            merge_result(self._search_player_highlight(player, away_team, kickoff_time))

        # 重複排除（keptのみ）
        unique_kept = self.filter.deduplicate(all_kept)

        # カテゴリ別にグルーピングしてmax_display件制限
        categories = [
            "press_conference",
            "historic",
            "tactical",
            "player_highlight",
        ]
        final_kept = []
        final_overflow = []

        for category in categories:
            max_display = get_youtube_max_display(category)
            cat_videos = [v for v in unique_kept if v.get("category") == category]
            if cat_videos:
                cat_videos = sorted(cat_videos, key=lambda v: v.get("published_at", ""), reverse=True)
                final_kept.extend(cat_videos[:max_display])
                if len(cat_videos) > max_display:
                    final_overflow.extend(cat_videos[max_display:])

        logger.info(
            f"Found {len(final_kept)} kept, {len(all_removed)} removed, {len(final_overflow)} overflow videos for {home_team} vs {away_team}"
        )

        return {"kept": final_kept, "removed": all_removed, "overflow": final_overflow}

    def process_matches(self, matches: list[MatchAggregate]) -> dict[str, list[dict]]:
        """全試合の動画を取得"""
        # モックモード: APIアクセスなしでリアルなダミーデータを返却
        if config.USE_MOCK_DATA:
            return self._get_mock_videos(matches)

        results = {}

        for match in matches:
            if match.core.is_target:
                # Issue #163: S/Aランクの試合のみ動画検索を実行（クォータ最適化）
                if match.core.rank not in ["S", "A", "Absolute"]:
                    logger.info(
                        f"Skipping YouTube search for low-rank match: {match.core.home_team} vs {match.core.away_team} (rank={match.core.rank})"
                    )
                    continue
                match_key = f"{match.core.home_team} vs {match.core.away_team}"
                results[match_key] = self.get_videos_for_match(match)

        return results

    def _get_mock_videos(self, matches: list[MatchAggregate]) -> dict[str, list[dict]]:
        """モック用YouTube動画データを取得"""
        from src.mock_provider import MockProvider

        return MockProvider.get_youtube_videos_for_matches(matches)
