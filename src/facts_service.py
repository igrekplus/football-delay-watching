from config import config
from .match_processor import MatchData
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
        import requests
        
        headers = {
            "X-RapidAPI-Key": config.RAPIDAPI_KEY,
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
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
        import requests
        
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/lineups"
        querystring = {"fixture": match.id}
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()
            
            for team_data in data.get('response', []):
                team_name = team_data['team']['name']
                formation = team_data['formation']
                start_xi = [p['player']['name'] for p in team_data['startXI']]
                subs = [p['player']['name'] for p in team_data['substitutes']]
                
                if team_name == match.home_team:
                    match.home_formation = formation
                    match.home_lineup = start_xi
                    match.home_bench = subs
                elif team_name == match.away_team:
                    match.away_formation = formation
                    match.away_lineup = start_xi
                    match.away_bench = subs

        except Exception as e:
            logger.error(f"Error fetching lineups for match {match.id}: {e}")
            match.error_status = config.ERROR_PARTIAL
    
    def _fetch_injuries(self, match: MatchData, headers: dict):
        import requests
        
        url = "https://api-football-v1.p.rapidapi.com/v3/injuries"
        querystring = {"fixture": match.id}
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
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
        import requests
        
        # Get fixture details which includes team IDs
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        querystring = {"id": match.id}
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
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
        import requests
        
        url = "https://api-football-v1.p.rapidapi.com/v3/teams/statistics"
        # Use current season - simplified approach
        import pytz
        from datetime import datetime
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        season = now.year if now.month >= 8 else now.year - 1
        
        querystring = {"team": team_id, "season": season, "league": 39}  # EPL
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
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
        # Populates facts: Venue, lineups, formation, etc. with MOCK DATA
        # In real impl, this would query an API based on match.id
        
        match.venue = "Etihad Stadium, Manchester" if "City" in match.home_team else "Stadium X"
        match.referee = "Michael Oliver"
        match.home_formation = "4-3-3"
        match.away_formation = "4-2-3-1"
        
        # Mock Lineups
        match.home_lineup = [f"Home Player {i}" for i in range(1, 12)]
        match.away_lineup = [f"Away Player {i}" for i in range(1, 12)]
        
        match.home_bench = [f"Home Sub {i}" for i in range(1, 8)]
        match.away_bench = [f"Away Sub {i}" for i in range(1, 8)]
        
        match.home_recent_form = "W-W-D-W-W"
        match.away_recent_form = "L-D-W-L-D"
        match.h2h_summary = "過去5試合: Home 2勝, 引分 1, Away 2勝"
        match.injuries_info = "Player A(Home): ハムストリング, Player B(Away): 出場停止"
    
    def _fetch_h2h(self, match: MatchData, headers: dict):
        """Fetch head-to-head history between the two teams"""
        import requests
        
        # First, get team IDs from fixture data
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        querystring = {"id": match.id}
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()
            
            if not data.get('response'):
                return
                
            fixture_data = data['response'][0]
            home_id = fixture_data['teams']['home']['id']
            away_id = fixture_data['teams']['away']['id']
            
            # Fetch H2H matches
            h2h_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"
            h2h_params = {"h2h": f"{home_id}-{away_id}", "last": 5}
            
            h2h_response = requests.get(h2h_url, headers=headers, params=h2h_params)
            h2h_data = h2h_response.json()
            
            if not h2h_data.get('response'):
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
            logger.error(f"Error fetching H2H for match {match.id}: {e}")
            match.h2h_summary = "取得エラー"
