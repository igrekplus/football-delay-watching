from config import config
from src.domain.models import MatchData
import logging
from typing import List

logger = logging.getLogger(__name__)

class FactsService:
    def __init__(self):
        pass

    def enrich_matches(self, matches: List[MatchData]):
        for match in matches:
            if match.is_target:
                self._get_facts(match)

    def _get_facts(self, match: MatchData):
        if config.USE_MOCK_DATA:
            self._get_mock_facts(match)
        else:
            self._fetch_facts_from_api(match)

    def _fetch_facts_from_api(self, match: MatchData):
        # import requests # Removed requests import
        from src.clients.cache import get_with_cache
        
        headers = {
            "x-apisports-key": config.API_FOOTBALL_KEY
        }
        
        # 1. Fetch Lineups
        self._fetch_lineups(match, headers)
        
        # 2. Fetch Injuries
        self._fetch_injuries(match, headers)
        
        # 3. Fetch Team Form (Recent Results)
        self._fetch_team_form(match, headers)
        
        # 4. Fetch Head-to-Head History
        self._fetch_h2h(match, headers)
    
    def _fetch_lineups(self, match: MatchData, headers: dict):
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        url = "https://v3.football.api-sports.io/fixtures/lineups"
        querystring = {"fixture": match.id}
        
        try:
            response = get_with_cache(url, headers=headers, params=querystring)
            data = response.json()
            
            # Collect player (id, lineup_name, number) pairs for nationality/photo lookup
            player_id_name_pairs = []
            
            for team_data in data.get('response', []):
                team_name = team_data['team']['name']
                formation = team_data['formation']
                
                # Extract coach name
                coach_name = team_data.get('coach', {}).get('name', '')
                
                # Extract player names, IDs, and numbers
                start_xi_data = [
                    (p['player']['name'], p['player']['id'], p['player'].get('number'))
                    for p in team_data['startXI']
                ]
                subs_data = [(p['player']['name'], p['player']['id']) for p in team_data['substitutes']]
                
                start_xi = [p[0] for p in start_xi_data]
                subs = [p[0] for p in subs_data]
                
                # Store player numbers (name -> number mapping)
                for name, _, number in start_xi_data:
                    if number is not None:
                        match.player_numbers[name] = number
                
                # Collect (player_id, lineup_name, team_name) tuples for starters only
                player_id_name_pairs.extend([(p[1], p[0], team_name) for p in start_xi_data])
                
                if team_name == match.home_team:
                    match.home_formation = formation
                    match.home_lineup = start_xi
                    match.home_bench = subs
                    match.home_manager = coach_name
                elif team_name == match.away_team:
                    match.away_formation = formation
                    match.away_lineup = start_xi
                    match.away_bench = subs
                    match.away_manager = coach_name
            
            # Fetch nationalities and photos for starters
            if not config.USE_MOCK_DATA and player_id_name_pairs:
                self._fetch_player_details(match, headers, player_id_name_pairs)

        except Exception as e:
            logger.error(f"Error fetching lineups for match {match.id}: {e}")
            match.error_status = config.ERROR_PARTIAL
    
    def _fetch_player_details(self, match: MatchData, headers: dict, player_id_name_pairs: list):
        """Fetch nationality and photo for each player using Players API
        
        Args:
            player_id_name_pairs: List of (player_id, lineup_name, team_name) tuples
        """
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        # Get season year
        import pytz
        from datetime import datetime
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        season = now.year if now.month >= 8 else now.year - 1
        
        for player_id, lineup_name, team_name in player_id_name_pairs:
            try:
                url = "https://v3.football.api-sports.io/players"
                querystring = {"id": player_id, "season": season}
                
                response = get_with_cache(url, headers=headers, params=querystring, team_name=team_name)
                data = response.json()
                
                if data.get('response'):
                    player_data = data['response'][0]
                    
                    # Get nationality
                    nationality = player_data['player'].get('nationality', '')
                    if nationality:
                        match.player_nationalities[lineup_name] = nationality
                    
                    # Get photo URL
                    photo = player_data['player'].get('photo', '')
                    if photo:
                        match.player_photos[lineup_name] = photo
                        
            except Exception as e:
                logger.warning(f"Error fetching details for player {player_id}: {e}")
                continue  # Continue with next player
    
    def _fetch_injuries(self, match: MatchData, headers: dict):
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        url = "https://v3.football.api-sports.io/injuries"
        querystring = {"fixture": match.id}
        
        try:
            response = get_with_cache(url, headers=headers, params=querystring)
            data = response.json()
            
            injuries = []
            for item in data.get('response', []):
                player_name = item['player']['name']
                team_name = item['team']['name']
                reason = item['player'].get('reason', 'Unknown')
                injuries.append(f"{player_name}({team_name}): {reason}")
            
            if injuries:
                match.injuries_info = ", ".join(injuries[:5])  # Max 5 entries
            else:
                match.injuries_info = "なし"
                
        except Exception as e:
            logger.error(f"Error fetching injuries for match {match.id}: {e}")
            # Keep default "不明"
    
    def _fetch_team_form(self, match: MatchData, headers: dict):
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        # Get fixture details which includes team IDs
        url = "https://v3.football.api-sports.io/fixtures"
        querystring = {"id": match.id}
        
        try:
            response = get_with_cache(url, headers=headers, params=querystring)
            data = response.json()
            
            if data.get('response'):
                fixture_data = data['response'][0]
                home_id = fixture_data['teams']['home']['id']
                away_id = fixture_data['teams']['away']['id']
                
                # Fetch form for each team
                match.home_recent_form = self._get_team_form(home_id, headers)
                match.away_recent_form = self._get_team_form(away_id, headers)
                
        except Exception as e:
            logger.error(f"Error fetching fixture details for match {match.id}: {e}")
    
    def _get_team_form(self, team_id: int, headers: dict) -> str:
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        url = "https://v3.football.api-sports.io/teams/statistics"
        # Use current season - simplified approach
        import pytz
        from datetime import datetime
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        season = now.year if now.month >= 8 else now.year - 1
        
        querystring = {"team": team_id, "season": season, "league": 39}  # EPL
        
        try:
            response = get_with_cache(url, headers=headers, params=querystring)
            data = response.json()
            
            if data.get('response'):
                form = data['response'].get('form', '')
                # Return last 5 characters (e.g., "WWDLW")
                return form[-5:] if form else ""
            return ""
            
        except Exception as e:
            logger.error(f"Error fetching team form for team {team_id}: {e}")
            return ""

    def _get_mock_facts(self, match: MatchData):
        # Real match data: Manchester City vs West Ham (2025-12-21)
        # Use actual player names, formations, and nationalities
        
        match.venue = "Etihad Stadium, Manchester"
        match.referee = "Paul Tierney, England"
        match.home_formation = "4-3-2-1"
        match.away_formation = "4-3-1-2"
        match.home_manager = "Pep Guardiola"
        match.away_manager = "Nuno Espirito Santo"
        
        # Manchester City Lineup (Real)
        match.home_lineup = [
            "G. Donnarumma", "M. Nunes", "R. Dias", "J. Gvardiol", "N. O'Reilly",
            "T. Reijnders", "Nico", "B. Silva",
            "R. Cherki", "P. Foden", "E. Haaland"
        ]
        # West Ham Lineup (Real)
        match.away_lineup = [
            "A. Areola", "K. Walker-Peters", "M. Kilman", "J. Todibo", "O. Scarles",
            "S. Magassa", "F. Potts", "M. Fernandes",
            "Lucas Paqueta", "J. Bowen", "C. Summerville"
        ]
        
        match.home_bench = ["J. Trafford", "N. Ake", "Savinho", "A. Khusanov", "C. Gray", "D. Mukasa", "R. Lewis"]
        match.away_bench = ["M. Hermansen", "Igor", "C. Wilson", "K. Mavropanos", "G. Rodriguez", "T. Soucek", "A. Irving"]
        
        match.home_recent_form = "WWWWW"
        match.away_recent_form = "LDDLL"
        match.h2h_summary = "過去5試合: Manchester City 5勝, 引分 0, West Ham 0勝"
        match.injuries_info = "R. Ait Nouri(MC): International duty, O. Bobb(MC): Hamstring, J. Doku(MC): Leg Injury"
        
        # Player numbers
        match.player_numbers = {
            "G. Donnarumma": 25, "M. Nunes": 27, "R. Dias": 3, "J. Gvardiol": 24, "N. O'Reilly": 33,
            "T. Reijnders": 4, "Nico": 14, "B. Silva": 20, "R. Cherki": 10, "P. Foden": 47, "E. Haaland": 9,
            "A. Areola": 23, "K. Walker-Peters": 2, "M. Kilman": 3, "J. Todibo": 25, "O. Scarles": 30,
            "S. Magassa": 27, "F. Potts": 32, "M. Fernandes": 18, "Lucas Paqueta": 10, "J. Bowen": 20, "C. Summerville": 7
        }
        
        # Player nationalities (Real)
        match.player_nationalities = {
            "G. Donnarumma": "Italy", "M. Nunes": "Portugal", "R. Dias": "Portugal",
            "J. Gvardiol": "Croatia", "N. O'Reilly": "England", "T. Reijnders": "Netherlands",
            "Nico": "Spain", "B. Silva": "Portugal", "R. Cherki": "France",
            "P. Foden": "England", "E. Haaland": "Norway",
            "A. Areola": "France", "K. Walker-Peters": "England", "M. Kilman": "England",
            "J. Todibo": "France", "O. Scarles": "England", "S. Magassa": "France",
            "F. Potts": "England", "M. Fernandes": "Portugal", "Lucas Paqueta": "Brazil",
            "J. Bowen": "England", "C. Summerville": "Netherlands"
        }
    
    def _fetch_h2h(self, match: MatchData, headers: dict):
        """Fetch head-to-head history between the two teams"""
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        # Issue #35: First, get team IDs from fixture data (直契約URLに統一)
        url = "https://v3.football.api-sports.io/fixtures"
        querystring = {"id": match.id}
        
        try:
            response = get_with_cache(url, headers=headers, params=querystring)
            data = response.json()
            
            if not data.get('response'):
                # Issue #35: 空レスポンス時のログ出力
                logger.warning(f"H2H: fixtures response empty for match {match.id}")
                match.h2h_summary = "対戦成績取得失敗（fixture取得エラー）"
                return
                
            fixture_data = data['response'][0]
            home_id = fixture_data['teams']['home']['id']
            away_id = fixture_data['teams']['away']['id']
            
            # Fetch H2H matches
            h2h_url = "https://v3.football.api-sports.io/fixtures/headtohead"
            h2h_params = {"h2h": f"{home_id}-{away_id}", "last": 5}
            
            h2h_response = get_with_cache(h2h_url, headers=headers, params=h2h_params)
            h2h_data = h2h_response.json()
            
            if not h2h_data.get('response'):
                logger.info(f"H2H: No history found for {match.home_team} vs {match.away_team}")
                match.h2h_summary = "対戦履歴なし"
                return
            
            # Count wins/draws (without revealing scores)
            home_wins = 0
            away_wins = 0
            draws = 0
            
            for fixture in h2h_data['response']:
                home_goals = fixture['goals']['home']
                away_goals = fixture['goals']['away']
                fixture_home_id = fixture['teams']['home']['id']
                
                if home_goals == away_goals:
                    draws += 1
                elif home_goals > away_goals:
                    # The team that played at home won
                    if fixture_home_id == home_id:
                        home_wins += 1
                    else:
                        away_wins += 1
                else:
                    # The away team won
                    if fixture_home_id == home_id:
                        away_wins += 1
                    else:
                        home_wins += 1
            
            total = home_wins + draws + away_wins
            match.h2h_summary = f"過去{total}試合: {match.home_team} {home_wins}勝, 引分 {draws}, {match.away_team} {away_wins}勝"
            
        except Exception as e:
            # Issue #35: エラー内容を明確にログ出力
            error_type = type(e).__name__
            logger.error(f"Error fetching H2H for match {match.id}: {error_type} - {e}")
            match.h2h_summary = f"対戦成績取得エラー（{error_type}）"
