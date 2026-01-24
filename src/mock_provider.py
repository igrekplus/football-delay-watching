"""
モックデータプロバイダー

fixtures/ 配下のJSONファイルからモックデータを読み込み、
各サービスで使用できる形式で提供する。

Issue #73: モックデータの外部化
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

import pytz

if TYPE_CHECKING:
    from src.domain.models import MatchAggregate, MatchData

logger = logging.getLogger(__name__)


class MockProvider:
    """モックデータを提供するクラス"""

    FIXTURES_DIR = Path(__file__).parent.parent / "mock_data"

    _cache: dict[str, Any] = {}

    @classmethod
    def _load_json(cls, relative_path: str) -> Any:
        """JSONファイルを読み込み（キャッシュ付き）"""
        if relative_path in cls._cache:
            return cls._cache[relative_path]

        file_path = cls.FIXTURES_DIR / relative_path

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            cls._cache[relative_path] = data
            return data
        except FileNotFoundError:
            logger.error(f"Mock fixture not found: {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            return None

    @classmethod
    def get_matches(cls) -> list["MatchAggregate"]:
        """
        試合データを取得

        Returns:
            MatchAggregate オブジェクトのリスト
        """
        from src.domain.models import MatchAggregate, MatchCore

        data = cls._load_json("match.json")
        if not data:
            return []

        utc = pytz.UTC
        matches = []

        for item in data:
            # kickoff_at_utc を datetime オブジェクトに変換
            kickoff_utc = None
            if item.get("kickoff_at_utc"):
                try:
                    kickoff_utc = datetime.fromisoformat(
                        item["kickoff_at_utc"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    kickoff_utc = utc.localize(datetime(2025, 12, 20, 15, 0, 0))

            # Create MatchCore
            core = MatchCore(
                id=item["id"],
                home_team=item["home_team"],
                away_team=item["away_team"],
                competition=item["competition"],
                kickoff_jst=item["kickoff_jst"],
                kickoff_local=item.get("kickoff_local", ""),
                rank=item.get("rank", "None"),
                venue=item.get("venue", ""),
                referee=item.get("referee", ""),
                home_logo=item.get("home_logo", ""),
                away_logo=item.get("away_logo", ""),
                competition_logo=item.get("competition_logo", ""),
                kickoff_at_utc=kickoff_utc,
            )
            matches.append(MatchAggregate(core=core))

        return matches

    @classmethod
    def apply_facts(cls, match: Union["MatchData", "MatchAggregate"]) -> None:
        """
        試合データにモックファクトを適用

        Args:
            match: MatchData オブジェクト（in-place で更新）
        """
        facts = cls._load_json("facts.json")

        if not facts:
            return

        # 基本情報
        match.venue = facts.get("venue", match.venue)
        match.referee = facts.get("referee", match.referee)
        match.home_formation = facts.get("home_formation", "")
        match.away_formation = facts.get("away_formation", "")
        match.home_manager = facts.get("home_manager", "")
        match.away_manager = facts.get("away_manager", "")

        # ラインナップ
        match.home_lineup = facts.get("home_lineup", [])
        match.away_lineup = facts.get("away_lineup", [])
        match.home_bench = facts.get("home_bench", [])
        match.away_bench = facts.get("away_bench", [])

        # フォーム・対戦履歴
        match.home_recent_form_details = facts.get("home_recent_form_details", [])
        match.away_recent_form_details = facts.get("away_recent_form_details", [])
        match.h2h_summary = facts.get("h2h_summary", "")
        match.h2h_details = facts.get("h2h_details", [])
        match.same_country_text = facts.get("same_country_text", "")
        match.former_club_trivia = facts.get("former_club_trivia", "")

        # 怪我人情報
        match.injuries_list = facts.get("injuries_list", [])
        if match.injuries_list:
            match.injuries_info = ", ".join(
                f"{i['name']}({i['team']}): {i['reason']}" for i in match.injuries_list
            )
        else:
            match.injuries_info = "なし"

        # 選手詳細情報
        match.player_numbers = facts.get("player_numbers", {})
        match.player_nationalities = facts.get("player_nationalities", {})
        match.player_birthdates = facts.get("player_birthdates", {})
        match.player_photos = facts.get("player_photos", {})

        # Issue #40: Instagram URL設定（CSVから読み込み）
        from settings.player_instagram import get_player_instagram_urls

        instagram_urls = get_player_instagram_urls()

        all_players = (
            match.home_lineup + match.home_bench + match.away_lineup + match.away_bench
        )

        for player_name in all_players:
            if player_name in instagram_urls:
                match.player_instagram[player_name] = instagram_urls[player_name]

    @classmethod
    def get_youtube_videos(cls, home_team: str, away_team: str) -> list[dict]:
        """
        YouTube動画データを取得

        Returns:
            動画データのリスト
        """
        videos = cls._load_json("youtube.json")

        if not videos:
            return []

        return videos

    @classmethod
    def get_youtube_videos_for_matches(
        cls, matches: list[Union["MatchData", "MatchAggregate"]]
    ) -> dict[str, list[dict]]:
        """
        複数試合のYouTube動画データを取得

        Returns:
            match_key -> 動画リストの辞書
        """
        results = {}

        for match in matches:
            if not match.core.is_target:
                continue

            match_key = f"{match.core.home_team} vs {match.core.away_team}"
            videos = cls.get_youtube_videos(match.core.home_team, match.core.away_team)
            results[match_key] = videos
            logger.info(
                f"[MOCK] YouTube: Returning {len(videos)} mock videos for {match_key}"
            )

        return results

    @classmethod
    def get_news(cls, home_team: str, away_team: str) -> list[dict[str, str]]:
        """
        ニュース記事データを取得

        Returns:
            記事データのリスト（プレースホルダーを置換済み）
        """
        data = cls._load_json("news.json")
        if not data:
            return []

        articles = []
        for item in data:
            articles.append(
                {
                    "content": item["content"].format(
                        home_team=home_team, away_team=away_team
                    ),
                    "title": item["title"].format(
                        home_team=home_team, away_team=away_team
                    ),
                    "source": item["source"],
                    "url": item["url"],
                    "relevance_score": item.get("relevance_score", 0),
                }
            )

        return articles

    @classmethod
    def get_news_summary(cls, home_team: str, away_team: str) -> str:
        """
        ニュース要約を取得

        Returns:
            要約テキスト（プレースホルダーを置換済み）
        """
        data = cls._load_json("llm.json")

        if not data or "news_summary" not in data:
            return f"[MOCK] ニュース要約: {home_team} vs {away_team}"

        return data["news_summary"].format(home_team=home_team, away_team=away_team)

    @classmethod
    def get_tactical_preview(cls, home_team: str, away_team: str) -> str:
        """
        戦術プレビューを取得

        Returns:
            プレビューテキスト（プレースホルダーを置換済み）
        """
        data = cls._load_json("llm.json")

        if not data or "tactical_preview" not in data:
            return f"[MOCK] 戦術プレビュー: {home_team} vs {away_team}"

        return data["tactical_preview"].format(home_team=home_team, away_team=away_team)

    @classmethod
    def get_interview_summary(
        cls, team_name: str, opponent_team: str, is_home: bool
    ) -> str:
        """インタビュー要約を取得"""
        data = cls._load_json("llm.json")
        if not data:
            return "監督: 『重要な試合になる。選手たちは準備できている。』"

        key = "home_interview" if is_home else "away_interview"
        return data.get(key, "監督: 『重要な試合になる。選手たちは準備できている。』")

    @classmethod
    def get_transfer_news(cls, team_name: str, match_date: str, is_home: bool) -> str:
        """移籍情報を取得"""
        data = cls._load_json("llm.json")
        if not data:
            return f"### {team_name} の移籍情報 (MOCK)\n\n- [MOCK] 情報なし"

        key = "home_transfer_news" if is_home else "away_transfer_news"
        return data.get(key, f"### {team_name} の移籍情報 (MOCK)\n\n- [MOCK] 情報なし")

    @classmethod
    def clear_cache(cls) -> None:
        """キャッシュをクリア（テスト用）"""
        cls._cache.clear()
