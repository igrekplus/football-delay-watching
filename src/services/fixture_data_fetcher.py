import logging
from typing import Dict, Any, Optional
from src.clients.api_football_client import ApiFootballClient
from src.domain.models import MatchData, MatchAggregate
from src.domain.match_raw_data import MatchRawData
from typing import Union

logger = logging.getLogger(__name__)

class FixtureDataFetcher:
    """
    試合データ取得を集約するサービス。
    同一試合に対する重複したAPI呼び出し（fixture/fetch_fixtures等）を最小限に抑える。
    """
    
    def __init__(self, api_client: ApiFootballClient = None):
        self.api = api_client or ApiFootballClient()
        self._fixture_cache: Dict[str, Dict[str, Any]] = {}

    def fetch_all(self, match: Union[MatchData, MatchAggregate]) -> MatchRawData:
        """
        指定された試合に関する全ての生データをAPIから一括取得する。
        """
        logger.info(f"Fetching all raw data for match {match.id} ({match.home_team} vs {match.away_team})")
        
        # 1. 試合の基本詳細を取得（Home/AwayのTeam IDを確定させるため）
        fixture = self._get_or_fetch_fixture(match.id)
        if not fixture:
            logger.error(f"Failed to fetch fixture details for {match.id}")
            # 空のデータを返す
            return MatchRawData(
                lineups={}, injuries={}, home_form={}, away_form={}, h2h={},
                home_team_id=0, away_team_id=0
            )

        home_id = fixture['teams']['home']['id']
        away_id = fixture['teams']['away']['id']

        # 2. 各種データの並列/逐次取得
        lineups = self.api.fetch_lineups(match.id)
        injuries = self.api.fetch_injuries(match.id)
        
        # 直近5試合（計算用に多めに取得: last=10）
        home_form = self.api.fetch_team_recent_fixtures(team_id=home_id, last=10)
        away_form = self.api.fetch_team_recent_fixtures(team_id=away_id, last=10)
        
        # 対戦履歴
        h2h = self.api.fetch_h2h(team1_id=home_id, team2_id=away_id)

        return MatchRawData(
            lineups=lineups,
            injuries=injuries,
            home_form=home_form,
            away_form=away_form,
            h2h=h2h,
            home_team_id=home_id,
            away_team_id=away_id,
            fixture_details=fixture
        )

    def _get_or_fetch_fixture(self, fixture_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """fixture詳細をキャッシュ付きで取得"""
        fid = str(fixture_id)
        if fid in self._fixture_cache:
            return self._fixture_cache[fid]
        
        data = self.api.fetch_fixtures(fixture_id=fid)
        if data.get('response') and len(data['response']) > 0:
            fixture = data['response'][0]
            self._fixture_cache[fid] = fixture
            return fixture
        
        return None
