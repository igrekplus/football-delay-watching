"""
試合データサービス

試合の詳細情報（スタメン、怪我人、フォーム、対戦履歴）の取得・加工を担当する。
API呼び出しはClientに委譲し、データ加工ロジックに専念する。
"""

import logging
from typing import List, Union

from config import config
from src.domain.models import MatchData, MatchAggregate
from src.clients.api_football_client import ApiFootballClient
from src.clients.llm_client import LLMClient
from settings.player_instagram import get_player_instagram_urls

logger = logging.getLogger(__name__)


class FactsService:
    """試合データ取得・加工サービス"""
    
    def __init__(self, api_client: ApiFootballClient = None, llm_client: LLMClient = None):
        """
        Args:
            api_client: API-Footballクライアント（DIで注入可能）
            llm_client: LLMクライアント（DIで注入可能）
        """
        self.api = api_client or ApiFootballClient()
        self.llm = llm_client or LLMClient()

    def enrich_matches(self, matches: List[Union[MatchData, MatchAggregate]]):
        """試合リストにデータを付加"""
        for match in matches:
            if match.is_target:
                self._get_facts(match)

    def _get_facts(self, match: Union[MatchData, MatchAggregate]):
        """試合データを取得"""
        if config.USE_MOCK_DATA:
            self._get_mock_facts(match)
        else:
            self._fetch_facts_from_api(match)

    def _fetch_facts_from_api(self, match: Union[MatchData, MatchAggregate]):
        """APIから試合データを取得"""
        # 1. Fetch Lineups
        self._fetch_lineups(match)
        
        # 2. Fetch Injuries
        self._fetch_injuries(match)
        
        # 3. Fetch Team Form
        self._fetch_team_form(match)
        
        # 4. Fetch Head-to-Head History
        self._fetch_h2h(match)
        
        # 5. Detect Same Country Matchups (Issue #39)
        self._detect_and_generate_same_country(match)
    
    def _fetch_lineups(self, match: Union[MatchData, MatchAggregate]):
        """スタメン情報を取得・加工"""
        data = self.api.fetch_lineups(match.id)
        
        if not data.get('response'):
            logger.error(f"No lineup data for match {match.id}")
            match.error_status = config.ERROR_PARTIAL
            return
        
        # Collect player (id, lineup_name, team_name) pairs for nationality/photo lookup
        player_id_name_pairs = []
        
        for team_data in data.get('response', []):
            team_name = team_data['team']['name']
            formation = team_data['formation']
            
            # Extract coach info (Issue #53)
            coach_name = team_data.get('coach', {}).get('name', '')
            coach_photo = team_data.get('coach', {}).get('photo', '')
            
            # Extract player data
            start_xi_data = [
                (p['player']['name'], p['player']['id'], p['player'].get('number'))
                for p in team_data['startXI']
            ]
            subs_data = [
                (p['player']['name'], p['player']['id'], p['player'].get('number'), p['player'].get('pos', ''))
                for p in team_data['substitutes']
            ]
            
            start_xi = [p[0] for p in start_xi_data]
            subs = [p[0] for p in subs_data]
            
            # Store player numbers
            for name, _, number in start_xi_data:
                if number is not None:
                    match.player_numbers[name] = number
            
            for name, _, number, pos in subs_data:
                if number is not None:
                    match.player_numbers[name] = number
                if pos:
                    match.player_positions[name] = pos
            
            # Collect player IDs for details lookup
            player_id_name_pairs.extend([(p[1], p[0], team_name) for p in start_xi_data])
            player_id_name_pairs.extend([(p[1], p[0], team_name) for p in subs_data])
            
            # Assign to match
            if team_name == match.home_team:
                match.home_formation = formation
                match.home_lineup = start_xi
                match.home_bench = subs
                match.home_manager = coach_name
                match.home_manager_photo = coach_photo
            elif team_name == match.away_team:
                match.away_formation = formation
                match.away_lineup = start_xi
                match.away_bench = subs
                match.away_manager = coach_name
                match.away_manager_photo = coach_photo
        
        # Fetch player details (nationality, photo, birthdate)
        if not config.USE_MOCK_DATA and player_id_name_pairs:
            self._fetch_player_details(match, player_id_name_pairs)
    
    def _fetch_player_details(self, match: Union[MatchData, MatchAggregate], player_id_name_pairs: list):
        """選手詳細情報を取得"""
        for player_id, lineup_name, team_name in player_id_name_pairs:
            try:
                data = self.api.fetch_player_details(
                    player_id=player_id,
                    team_name=team_name
                )
                
                if data.get('response'):
                    player_data = data['response'][0]
                    
                    nationality = player_data['player'].get('nationality', '')
                    if nationality:
                        match.player_nationalities[lineup_name] = nationality
                    
                    photo = player_data['player'].get('photo', '')
                    if photo:
                        match.player_photos[lineup_name] = photo
                    
                    birth_date = player_data['player'].get('birth', {}).get('date', '')
                    if birth_date:
                        match.player_birthdates[lineup_name] = birth_date
                        
            except Exception as e:
                logger.warning(f"Error fetching details for player {player_id}: {e}")
                continue
        
        # Issue #40: Instagram URL設定（CSVから）
        self._set_instagram_urls(match)
    
    def _set_instagram_urls(self, match: Union[MatchData, MatchAggregate]):
        """選手のInstagram URLをCSVから設定"""
        instagram_urls = get_player_instagram_urls()
        
        # 両チームの全選手に対してInstagram URLを設定
        all_players = (
            match.home_lineup + match.home_bench +
            match.away_lineup + match.away_bench
        )
        
        for player_name in all_players:
            if player_name in instagram_urls:
                match.player_instagram[player_name] = instagram_urls[player_name]
        
        if match.player_instagram:
            logger.debug(f"Set Instagram URLs for {len(match.player_instagram)} players")
    
    def _fetch_injuries(self, match: Union[MatchData, MatchAggregate]):
        """怪我人情報を取得・加工"""
        data = self.api.fetch_injuries(match.id)
        
        injuries = []
        for item in data.get('response', []):
            player_name = item['player']['name']
            team_name = item['team']['name']
            reason = item['player'].get('reason', 'Unknown')
            photo = item['player'].get('photo', '')
            
            injuries.append({
                "name": player_name,
                "team": team_name,
                "reason": reason,
                "photo": photo
            })
            
            if photo:
                match.player_photos[player_name] = photo
        
        if injuries:
            match.injuries_list = injuries[:5]
            match.injuries_info = ", ".join(
                f"{i['name']}({i['team']}): {i['reason']}" for i in match.injuries_list
            )
        else:
            match.injuries_list = []
            match.injuries_info = "なし"
    
    def _fetch_team_form(self, match: Union[MatchData, MatchAggregate]):
        """チームフォームを取得"""
        # Get fixture details for team IDs
        fixture_data = self.api.fetch_fixtures(fixture_id=match.id)
        
        if not fixture_data.get('response'):
            return
        
        fixture = fixture_data['response'][0]
        home_id = fixture['teams']['home']['id']
        away_id = fixture['teams']['away']['id']
        
        league_id = config.LEAGUE_IDS.get(match.competition, 39)
        
        # Fetch form for each team
        match.home_recent_form = self._get_team_form(home_id, league_id)
        match.away_recent_form = self._get_team_form(away_id, league_id)
    
    def _get_team_form(self, team_id: int, league_id: int) -> str:
        """チームの直近フォームを取得"""
        data = self.api.fetch_team_statistics(team_id=team_id, league_id=league_id)
        
        if data.get('response'):
            form = data['response'].get('form', '')
            return form[-5:] if form else ""
        return ""
    
    def _fetch_h2h(self, match: Union[MatchData, MatchAggregate]):
        """対戦履歴を取得・加工（過去5年間のみ）"""
        from datetime import datetime, timedelta
        
        # Get fixture details for team IDs
        fixture_data = self.api.fetch_fixtures(fixture_id=match.id)
        
        if not fixture_data.get('response'):
            logger.warning(f"H2H: fixtures response empty for match {match.id}")
            match.h2h_summary = "対戦成績取得失敗（fixture取得エラー）"
            return
        
        fixture = fixture_data['response'][0]
        home_id = fixture['teams']['home']['id']
        away_id = fixture['teams']['away']['id']
        
        # Fetch H2H
        h2h_data = self.api.fetch_h2h(team1_id=home_id, team2_id=away_id)
        
        if not h2h_data.get('response'):
            logger.info(f"H2H: No history found for {match.home_team} vs {match.away_team}")
            match.h2h_summary = "対戦履歴なし"
            match.h2h_details = []
            return
        
        # Filter to last 5 years
        cutoff_date = config.TARGET_DATE - timedelta(days=5*365)
        filtered_matches = []
        
        for h2h_fixture in h2h_data['response']:
            fixture_date_str = h2h_fixture.get('fixture', {}).get('date', '')
            if not fixture_date_str:
                continue
            
            try:
                fixture_date = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
                if fixture_date.replace(tzinfo=None) < cutoff_date:
                    continue
            except (ValueError, TypeError):
                continue
            
            filtered_matches.append(h2h_fixture)
        
        # Sort by date descending
        filtered_matches.sort(
            key=lambda x: x.get('fixture', {}).get('date', ''),
            reverse=True
        )
        
        if not filtered_matches:
            logger.info(f"H2H: No matches within last 5 years for {match.home_team} vs {match.away_team}")
            match.h2h_summary = "過去5年間の対戦なし"
            match.h2h_details = []
            return
        
        # Build h2h_details and count wins/draws
        h2h_details = []
        home_wins = 0
        away_wins = 0
        draws = 0
        
        for h2h_fixture in filtered_matches:
            fixture_info = h2h_fixture.get('fixture', {})
            league_info = h2h_fixture.get('league', {})
            goals = h2h_fixture.get('goals', {})
            teams = h2h_fixture.get('teams', {})
            
            fixture_date_str = fixture_info.get('date', '')[:10]  # YYYY-MM-DD
            competition = league_info.get('name', 'Unknown')
            home_team_name = teams.get('home', {}).get('name', '')
            away_team_name = teams.get('away', {}).get('name', '')
            home_goals = goals.get('home', 0) or 0
            away_goals = goals.get('away', 0) or 0
            score = f"{home_goals}-{away_goals}"
            fixture_home_id = teams.get('home', {}).get('id')
            
            # Determine winner relative to the current match's home team
            if home_goals == away_goals:
                winner = "draw"
                draws += 1
            elif home_goals > away_goals:
                if fixture_home_id == home_id:
                    winner = match.home_team
                    home_wins += 1
                else:
                    winner = match.away_team
                    away_wins += 1
            else:
                if fixture_home_id == home_id:
                    winner = match.away_team
                    away_wins += 1
                else:
                    winner = match.home_team
                    home_wins += 1
            
            h2h_details.append({
                "date": fixture_date_str,
                "competition": competition,
                "home": home_team_name,
                "away": away_team_name,
                "score": score,
                "winner": winner
            })
        
        match.h2h_details = h2h_details
        total = home_wins + draws + away_wins
        match.h2h_summary = f"過去5年間 {total}試合: {match.home_team} {home_wins}勝, 引分 {draws}, {match.away_team} {away_wins}勝"

    def _get_mock_facts(self, match: Union[MatchData, MatchAggregate]):
        """モックデータを設定"""
        from src.mock_provider import MockProvider
        MockProvider.apply_facts(match)
        # モックモードでも同国対決を検出・生成
        self._detect_and_generate_same_country(match)
    
    def _detect_same_country_matchups(self, match: Union[MatchData, MatchAggregate]) -> list:
        """同国対決を検出（Issue #39）"""
        home_players = match.home_lineup + match.home_bench
        away_players = match.away_lineup + match.away_bench
        
        # 国籍ごとにグループ化
        home_by_country = {}
        away_by_country = {}
        
        for player in home_players:
            country = match.player_nationalities.get(player, "")
            if country:
                home_by_country.setdefault(country, []).append(player)
        
        for player in away_players:
            country = match.player_nationalities.get(player, "")
            if country:
                away_by_country.setdefault(country, []).append(player)
        
        # 両チームに存在する国籍を抽出（イングランド以外、注目度が高い国籍のみ）
        # 注: イングランドはプレミアリーグでは多すぎるので除外
        excluded_countries = {"England", "Spain", "Germany", "France", "Italy"}
        common_countries = (set(home_by_country.keys()) & set(away_by_country.keys())) - excluded_countries
        
        matchups = []
        for country in common_countries:
            matchups.append({
                "country": country,
                "home_players": home_by_country[country],
                "away_players": away_by_country[country]
            })
        
        return matchups
    
    def _detect_and_generate_same_country(self, match: Union[MatchData, MatchAggregate]):
        """同国対決を検出し、関係性テキストを生成（Issue #39）"""
        matchups = self._detect_same_country_matchups(match)
        match.same_country_matchups = matchups
        
        if matchups:
            logger.info(f"Detected same country matchups: {[m['country'] for m in matchups]}")
            # LLMで関係性・小ネタを生成
            match.same_country_text = self.llm.generate_same_country_trivia(
                home_team=match.home_team,
                away_team=match.away_team,
                matchups=matchups
            )
        else:
            match.same_country_text = ""

