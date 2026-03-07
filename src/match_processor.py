import logging
import os
from datetime import datetime, timedelta
from typing import Any

from config import config
from src.clients.api_football_client import ApiFootballClient
from src.domain.match_ranker import MatchRanker
from src.domain.match_selector import MatchSelector
from src.domain.models import MatchAggregate, MatchCore
from src.mock_provider import MockProvider
from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)


class MatchProcessor:
    """
    Orchestrates the retrieval, ranking, and selection of matches.
    """

    def __init__(self):
        self.client = ApiFootballClient()
        self.ranker = MatchRanker()
        self.selector = MatchSelector()

    def run(self) -> list[MatchAggregate]:
        matches = self.extract_matches()

        # Calculate Rank for all matches
        for m in matches:
            self.ranker.assign_rank(m)

        # 選定はワークフロー側で行う（スケジュール判定後）
        return matches

    def extract_matches(self) -> list[MatchAggregate]:
        if config.USE_MOCK_DATA:
            return MockProvider.get_matches()
        else:
            return self._fetch_matches_from_api()

    def _fetch_matches_from_api(self) -> list[MatchAggregate]:
        """Fetch and parse matches from API-Football."""
        matches = []
        target_date = config.TARGET_DATE
        target_fixture_id = os.getenv("TARGET_FIXTURE_ID", "").strip()

        if target_fixture_id:
            logger.info(f"TARGET_FIXTURE_ID override enabled: {target_fixture_id}")
            return self._fetch_match_by_fixture_id(target_fixture_id, target_date)

        # デバッグモード: 過去24時間の試合を取得するため、今日と昨日の両方を検索
        # 本番モード(Dynamic Schedule): 現在時刻周辺の試合を拾うため、同様に複数日を検索
        # Target Date (Yesterday) AND Target Date + 1 (Today)
        # これにより、日付を跨ぐ深夜帯や、当日夜の試合も漏らさず取得する
        if not config.USE_MOCK_DATA:
            dates_to_search = [
                DateTimeUtil.format_date_str(target_date),
                DateTimeUtil.format_date_str(target_date + timedelta(days=1)),
            ]
        else:
            dates_to_search = [DateTimeUtil.format_date_str(target_date)]

        logger.info(f"Fetching matches for dates: {dates_to_search}")

        # Calculate Season
        season_year = (
            target_date.year if target_date.month >= 6 else target_date.year - 1
        )

        target_league_ids = config.LEAGUE_IDS

        for date_str in dates_to_search:
            for league_name, league_id in target_league_ids.items():
                if league_name not in config.TARGET_LEAGUES:
                    continue

                data = self.client.get_fixtures(league_id, season_year, date_str)

                # Parse response
                for item in data.get("response", []):
                    match_data = self._parse_match_data(item, league_name, target_date)
                    if match_data:
                        matches.append(match_data)

        return matches

    def _fetch_match_by_fixture_id(
        self, fixture_id: str, target_date: datetime
    ) -> list[MatchAggregate]:
        """Fetch exactly one fixture when a manual override is provided."""
        matches: list[MatchAggregate] = []
        data = self.client.fetch_fixtures(fixture_id=fixture_id)

        for item in data.get("response", []):
            league_name = self._resolve_league_name(item.get("league", {}))
            match_data = self._parse_match_data(
                item,
                league_name,
                target_date,
                skip_time_window=True,
            )
            if match_data:
                matches.append(match_data)

        if not matches:
            logger.warning(f"No match found for TARGET_FIXTURE_ID={fixture_id}")

        return matches

    def _resolve_league_name(self, league: dict[str, Any]) -> str:
        """Map API league metadata to the project's competition key when possible."""
        league_id = league.get("id")

        for league_name, configured_id in config.LEAGUE_IDS.items():
            if configured_id == league_id:
                return league_name

        return league.get("name", "Unknown")

    def _parse_match_data(
        self,
        item: dict[str, Any],
        league_name: str,
        target_date: datetime,
        skip_time_window: bool = False,
    ) -> MatchAggregate | None:
        """Parses a single match item and returns a MatchAggregate."""
        fixture = item["fixture"]
        teams = item["teams"]

        # Check status (Skip Cancelled/Postponed)
        status = fixture["status"]["short"]
        if status in ["CANC", "PST", "ABD", "AWD", "WO"]:
            return None

        # Timezone conversion
        match_date_utc = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        match_date_jst = DateTimeUtil.to_jst(match_date_utc)
        match_date_local = (
            match_date_utc  # Placeholder for local time (could be improved)
        )

        # Time window filter
        if not skip_time_window and not self._is_within_time_window(
            match_date_jst, target_date
        ):
            return None

        # Extract Venue
        venue_name = fixture.get("venue", {}).get("name", "Unknown Venue")
        venue_city = fixture.get("venue", {}).get("city", "")
        venue_full = f"{venue_name}, {venue_city}" if venue_city else venue_name

        # Team Logos
        home_logo_url = teams["home"].get("logo", "")
        away_logo_url = teams["away"].get("logo", "")

        # League Logo (Issue #116)
        league_logo_url = item.get("league", {}).get("logo", "")

        # Create MatchCore
        core = MatchCore(
            id=str(fixture["id"]),
            home_team=teams["home"]["name"],
            away_team=teams["away"]["name"],
            competition=league_name,
            league_id=item["league"]["id"],
            match_round=item["league"].get("round", ""),
            kickoff_jst=DateTimeUtil.format_jst_display(
                match_date_jst, include_weekday=True
            ),
            kickoff_local=match_date_local.strftime("%Y-%m-%d %H:%M Local"),
            rank="None",  # Calculated later by MatchRanker
            venue=venue_full,
            referee=fixture.get("referee", "Unknown"),
            home_logo=home_logo_url,
            away_logo=away_logo_url,
            competition_logo=league_logo_url,
            kickoff_at_utc=match_date_utc,
        )

        # Wrap in MatchAggregate and return
        return MatchAggregate(core=core)

    def _is_within_time_window(
        self, match_date_jst: datetime, target_date: datetime
    ) -> bool:
        """Checks if the match is within the target time window."""
        # If TARGET_DATE is explicitly set, use production-like window logic relative to that date
        if os.getenv("TARGET_DATE"):
            # Assuming manual override wants strict day bucket + buffer
            window_end = target_date + timedelta(days=1)
            window_start = target_date - timedelta(hours=3)
        else:
            # Dynamic Schedule (Production & Debug)
            # MatchScheduler handles strict filtering (Now - 1h <= Kickoff <= Now + 24h).
            # MatchProcessor should be permissive and let MatchScheduler decide.

            now_jst = DateTimeUtil.now_jst()

            # Allow matches from 24h ago up to 48h future (wide net)
            window_end = now_jst + timedelta(hours=48)
            window_start = now_jst - timedelta(hours=24)

        return window_start <= match_date_jst < window_end
