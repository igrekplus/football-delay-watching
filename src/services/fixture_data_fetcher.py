from __future__ import annotations

import logging
from typing import Any

from src.clients.api_football_client import ApiFootballClient
from src.domain.match_raw_data import MatchRawData
from src.domain.models import MatchAggregate

logger = logging.getLogger(__name__)


class FixtureDataFetcher:
    """
    試合データ取得を集約するサービス。
    同一試合に対する重複したAPI呼び出しを最小限に抑える。
    """

    def __init__(self, api_client: ApiFootballClient = None):
        self.api = api_client or ApiFootballClient()
        self._fixture_cache: dict[str, dict[str, Any]] = {}

    def fetch_all(self, match: MatchAggregate) -> MatchRawData:
        """
        指定された試合に関する全ての生データをAPIから一括取得する。
        """
        logger.info(
            f"Fetching all raw data for match {match.core.id} ({match.core.home_team} vs {match.core.away_team})"
        )

        # 1. 試合の基本詳細を取得（Home/AwayのTeam IDを確定させるため）
        fixture = self._get_or_fetch_fixture(match.core.id)
        if not fixture:
            logger.error(f"Failed to fetch fixture details for {match.core.id}")
            # 空のデータを返す
            return MatchRawData(
                lineups={},
                injuries={},
                home_form={},
                away_form={},
                h2h={},
                home_team_id=0,
                away_team_id=0,
            )

        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]

        # 2. 各種データの並列/逐次取得
        lineups = self.api.fetch_lineups(match.core.id)
        injuries = self.api.fetch_injuries(match.core.id)

        # 直近5試合（計算用に多めに取得: last=10）
        home_form = self.api.fetch_team_recent_fixtures(team_id=home_id, last=10)
        away_form = self.api.fetch_team_recent_fixtures(team_id=away_id, last=10)

        # 対戦履歴
        h2h = self.api.fetch_h2h(team1_id=home_id, team2_id=away_id)

        # 3. 順位表の取得 (Issue #192) - リーグ戦のみ、週単位キャッシュ利用
        standings = None
        # リーグ戦（EPL, LALIGA）のみ順位表を表示
        if home_id != 0 and match.core.competition in ["EPL", "LALIGA"]:
            from src.utils.datetime_util import DateTimeUtil
            from src.utils.standings_cache import (
                get_week_key,
                has_standings,
                load_standings,
                save_standings,
            )

            # キックオフの月曜日キーを取得
            match_date_jst = DateTimeUtil.to_jst(match.core.kickoff_at_utc)
            week_key = get_week_key(match_date_jst)
            league_name = match.core.competition

            if has_standings(week_key, league_name):
                logger.info(f"Loading standings from cache: {league_name} {week_key}")
                standings = load_standings(week_key, league_name)
            else:
                logger.info(f"Fetching standings from API: {league_name} {week_key}")
                season = (
                    match_date_jst.year
                    if match_date_jst.month >= 6
                    else match_date_jst.year - 1
                )
                data = self.api.fetch_standings(match.core.league_id, season)
                if data.get("response"):
                    # 通常、[0]["league"]["standings"][0] に順位表リストが入っている
                    try:
                        raw_standings = data["response"][0]["league"]["standings"][0]
                        save_standings(week_key, league_name, raw_standings)
                        standings = raw_standings
                    except (IndexError, KeyError) as e:
                        logger.error(f"Error parsing standings API response: {e}")

        return MatchRawData(
            lineups=lineups,
            injuries=injuries,
            home_form=home_form,
            away_form=away_form,
            h2h=h2h,
            standings=standings,
            home_team_id=home_id,
            away_team_id=away_id,
            fixture_details=fixture,
        )

    def _get_or_fetch_fixture(self, fixture_id: str) -> dict[str, Any] | None:
        """fixture詳細をキャッシュ付きで取得"""
        fid = str(fixture_id)
        if fid in self._fixture_cache:
            return self._fixture_cache[fid]

        data = self.api.fetch_fixtures(fixture_id=fid)
        if data.get("response") and len(data["response"]) > 0:
            fixture = data["response"][0]
            self._fixture_cache[fid] = fixture
            return fixture

        return None
