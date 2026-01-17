"""
試合データサービス

FixtureDataFetcher, FactsFormatter, TributeGenerator を統括する Facade サービス。
既存の呼び出し元（MatchProcessor等）のインターフェースを維持しつつ、
実際の処理を各サービスへ委譲する。
"""

import logging

from config import config
from settings.player_instagram import get_player_instagram_urls
from src.clients.api_football_client import ApiFootballClient
from src.clients.llm_client import LLMClient
from src.domain.models import MatchAggregate
from src.mock_provider import MockProvider
from src.services.facts_formatter import FactsFormatter
from src.services.fixture_data_fetcher import FixtureDataFetcher
from src.services.tribute_generator import TributeGenerator

logger = logging.getLogger(__name__)


class FactsService:
    """試合データ取得・加工サービス (Facade)"""

    def __init__(
        self, api_client: ApiFootballClient = None, llm_client: LLMClient = None
    ):
        self.api = api_client or ApiFootballClient()
        self.llm = llm_client or LLMClient()

        # サブサービスの初期化
        self.fetcher = FixtureDataFetcher(self.api)
        self.formatter = FactsFormatter()
        self.tribute = TributeGenerator(self.llm)

    def enrich_matches(self, matches: list[MatchAggregate]):
        """試合リストにデータを付加"""
        for match in matches:
            if match.core.is_target:
                self._enrich_single(match)

    def _enrich_single(self, match: MatchAggregate):
        """1試合に対してデータを補完する"""
        if config.USE_MOCK_DATA:
            logger.info(
                f"Applying mock facts for {match.core.home_team} vs {match.core.away_team}"
            )
            MockProvider.apply_facts(match)
            # モックモードでも同国対決を検出・生成
            if not match.facts.same_country_text:
                self.tribute.detect_and_generate_same_country(match)
            return

        # 1. APIからのデータ一括取得
        raw = self.fetcher.fetch_all(match)

        # 2. データの整形と流し込み
        # lineups & player details
        player_id_pairs = self.formatter.format_lineups(match, raw.lineups)
        if player_id_pairs:
            self._fetch_player_details(match, player_id_pairs)

        # Instagram URL
        self._set_instagram_urls(match)

        # Injuries
        self.formatter.format_injuries(match, raw.injuries)

        # Recent Form
        self.formatter.format_recent_form(match, raw.home_form, raw.away_form)

        # H2H
        self.formatter.format_h2h(match, raw.h2h, raw.home_team_id)

        # 3. LLMによるトリビア生成
        self.tribute.detect_and_generate_same_country(match)
        self.tribute.generate_former_club_trivia(match)

    def _fetch_player_details(self, match: MatchAggregate, player_id_name_pairs: list):
        """選手詳細情報（国籍、写真等）を取得"""
        for player_id, lineup_name, team_name in player_id_name_pairs:
            try:
                data = self.api.fetch_player_details(
                    player_id=player_id, team_name=team_name
                )

                if data.get("response"):
                    player_data = data["response"][0]

                    nationality = player_data["player"].get("nationality", "")
                    if nationality:
                        match.facts.player_nationalities[lineup_name] = nationality

                    photo = player_data["player"].get("photo", "")
                    if photo:
                        match.facts.player_photos[lineup_name] = photo

                    birth_date = player_data["player"].get("birth", {}).get("date", "")
                    if birth_date:
                        match.facts.player_birthdates[lineup_name] = birth_date

            except Exception as e:
                logger.warning(f"Error fetching details for player {player_id}: {e}")
                continue

    def _set_instagram_urls(self, match: MatchAggregate):
        """選手のInstagram URLをCSVから設定"""
        instagram_urls = get_player_instagram_urls()

        all_players = (
            match.facts.home_lineup
            + match.facts.home_bench
            + match.facts.away_lineup
            + match.facts.away_bench
        )

        for player_name in all_players:
            if player_name in instagram_urls:
                match.facts.player_instagram[player_name] = instagram_urls[player_name]

        if match.facts.player_instagram:
            logger.debug(
                f"Set Instagram URLs for {len(match.facts.player_instagram)} players"
            )
