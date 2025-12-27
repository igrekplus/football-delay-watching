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
                
                # Extract coach name and photo (Issue #53)
                coach_name = team_data.get('coach', {}).get('name', '')
                coach_photo = team_data.get('coach', {}).get('photo', '')
                
                # Extract player names, IDs, and numbers
                start_xi_data = [
                    (p['player']['name'], p['player']['id'], p['player'].get('number'))
                    for p in team_data['startXI']
                ]
                # ベンチ選手のポジションと背番号も取得
                subs_data = [
                    (p['player']['name'], p['player']['id'], p['player'].get('number'), p['player'].get('pos', ''))
                    for p in team_data['substitutes']
                ]
                
                start_xi = [p[0] for p in start_xi_data]
                subs = [p[0] for p in subs_data]
                
                # Store player numbers (name -> number mapping) for starters
                for name, _, number in start_xi_data:
                    if number is not None:
                        match.player_numbers[name] = number
                
                # Store player numbers and positions for bench players
                for name, _, number, pos in subs_data:
                    if number is not None:
                        match.player_numbers[name] = number
                    if pos:
                        match.player_positions[name] = pos
                
                # Collect (player_id, lineup_name, team_name) tuples for starters and subs
                player_id_name_pairs.extend([(p[1], p[0], team_name) for p in start_xi_data])
                player_id_name_pairs.extend([(p[1], p[0], team_name) for p in subs_data])
                
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
                    
                    # Get birth date (Issue #43)
                    birth_date = player_data['player'].get('birth', {}).get('date', '')
                    if birth_date:
                        match.player_birthdates[lineup_name] = birth_date
                        
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
                photo = item['player'].get('photo', '')
                
                # 構造化データとして保存（写真URL含む）
                injuries.append({
                    "name": player_name,
                    "team": team_name,
                    "reason": reason,
                    "photo": photo
                })
                
                # player_photos 辞書にも追加（他の場所でも参照可能に）
                if photo:
                    match.player_photos[player_name] = photo
            
            if injuries:
                match.injuries_list = injuries[:5]  # Max 5 entries
                # フォールバック用テキストも生成
                match.injuries_info = ", ".join(
                    f"{i['name']}({i['team']}): {i['reason']}" for i in match.injuries_list
                )
            else:
                match.injuries_list = []
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
                match.home_recent_form = self._get_team_form(home_id, headers, match.competition)
                match.away_recent_form = self._get_team_form(away_id, headers, match.competition)
                
        except Exception as e:
            logger.error(f"Error fetching fixture details for match {match.id}: {e}")
    
    def _get_team_form(self, team_id: int, headers: dict, competition: str) -> str:
        # import requests # Removed
        from src.clients.cache import get_with_cache
        
        url = "https://v3.football.api-sports.io/teams/statistics"
        # Use current season - simplified approach
        import pytz
        from datetime import datetime
        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)
        season = now.year if now.month >= 8 else now.year - 1
        
        # Get league ID based on competition
        league_id = config.LEAGUE_IDS.get(competition, 39)
        querystring = {"team": team_id, "season": season, "league": league_id}
        
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
        # ベンチ選手（デバッグ実行から取得した正確なデータ）
        match.home_bench = ["J. Trafford", "N. Ake", "Savinho", "A. Khusanov", "C. Gray", "D. Mukasa", "R. Lewis", "S. Mfuni", "R. Heskey"]
        match.away_bench = ["M. Hermansen", "Igor", "C. Wilson", "K. Mavropanos", "G. Rodriguez", "T. Soucek", "A. Irving", "M. Kante", "E. Mayers"]
        
        match.home_recent_form = "WWWWW"
        match.away_recent_form = "LDDLL"
        match.h2h_summary = "過去5試合: Manchester City 5勝, 引分 0, West Ham 0勝"
        
        # 怪我人・出場停止情報（構造化データ）- 実APIレスポンスから取得した正確なデータ
        match.injuries_list = [
            {"name": "R. Ait Nouri", "team": "Manchester City", "reason": "International duty", "photo": "https://media.api-sports.io/football/players/21138.png"},
            {"name": "O. Bobb", "team": "Manchester City", "reason": "Hamstring Injury", "photo": "https://media.api-sports.io/football/players/278133.png"},
            {"name": "J. Doku", "team": "Manchester City", "reason": "Leg Injury", "photo": "https://media.api-sports.io/football/players/1422.png"},
            {"name": "M. Kovacic", "team": "Manchester City", "reason": "Heel Injury", "photo": "https://media.api-sports.io/football/players/2291.png"},
            {"name": "O. Marmoush", "team": "Manchester City", "reason": "International duty", "photo": "https://media.api-sports.io/football/players/81573.png"},
        ]
        match.injuries_info = ", ".join(
            f"{i['name']}({i['team']}): {i['reason']}" for i in match.injuries_list
        )
        
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
            "J. Bowen": "England", "C. Summerville": "Netherlands",
            # Bench players
            "J. Trafford": "England", "N. Ake": "Netherlands", "Savinho": "Brazil",
            "A. Khusanov": "Uzbekistan", "C. Gray": "Jamaica", "D. Mukasa": "England", "R. Lewis": "England",
            "M. Hermansen": "Denmark", "Igor": "Brazil", "C. Wilson": "England",
            "K. Mavropanos": "Greece", "G. Rodriguez": "Uruguay", "T. Soucek": "Czech Republic", "A. Irving": "England"
        }
        
        # Player birthdates (Issue #43) - スタメン＋ベンチ
        match.player_birthdates = {
            # Manchester City starters
            "G. Donnarumma": "1999-02-25", "M. Nunes": "1998-08-27", "R. Dias": "1997-05-14",
            "J. Gvardiol": "2002-01-23", "N. O'Reilly": "2003-07-15", "T. Reijnders": "1998-07-29",
            "Nico": "2003-09-02", "B. Silva": "1994-08-10", "R. Cherki": "2003-08-17",
            "P. Foden": "2000-05-28", "E. Haaland": "2000-07-21",
            # West Ham starters
            "A. Areola": "1993-02-27", "K. Walker-Peters": "1997-04-13", "M. Kilman": "1997-05-23",
            "J. Todibo": "1999-12-28", "O. Scarles": "2005-03-10", "S. Magassa": "2004-06-12",
            "F. Potts": "2005-09-25", "M. Fernandes": "1999-09-08", "Lucas Paqueta": "1997-08-27",
            "J. Bowen": "1996-11-20", "C. Summerville": "2001-10-02",
            # Manchester City bench
            "J. Trafford": "2002-10-10", "N. Ake": "1995-02-18", "Savinho": "2004-04-10",
            "A. Khusanov": "2004-04-29", "C. Gray": "2000-09-06", "D. Mukasa": "2005-01-20", "R. Lewis": "2005-09-21",
            # West Ham bench
            "M. Hermansen": "2000-07-13", "Igor": "1998-02-07", "C. Wilson": "1992-11-18",
            "K. Mavropanos": "1997-12-11", "G. Rodriguez": "2003-11-14", "T. Soucek": "1995-02-27", "A. Irving": "2003-04-18"
        }
        
        # Player photos (API-Footballのプレイヤー画像URL形式)
        match.player_photos = {
            # Manchester City starters
            "G. Donnarumma": "https://media.api-sports.io/football/players/1622.png",
            "M. Nunes": "https://media.api-sports.io/football/players/41621.png",
            "R. Dias": "https://media.api-sports.io/football/players/567.png",
            "J. Gvardiol": "https://media.api-sports.io/football/players/129033.png",
            "N. O'Reilly": "https://media.api-sports.io/football/players/307123.png",
            "T. Reijnders": "https://media.api-sports.io/football/players/36902.png",
            "Nico": "https://media.api-sports.io/football/players/161933.png",
            "B. Silva": "https://media.api-sports.io/football/players/636.png",
            "R. Cherki": "https://media.api-sports.io/football/players/156477.png",
            "P. Foden": "https://media.api-sports.io/football/players/631.png",
            "E. Haaland": "https://media.api-sports.io/football/players/1100.png",
            # West Ham starters
            "A. Areola": "https://media.api-sports.io/football/players/253.png",
            "K. Walker-Peters": "https://media.api-sports.io/football/players/171.png",
            "M. Kilman": "https://media.api-sports.io/football/players/18744.png",
            "J. Todibo": "https://media.api-sports.io/football/players/138.png",
            "O. Scarles": "https://media.api-sports.io/football/players/327730.png",
            "S. Magassa": "https://media.api-sports.io/football/players/326176.png",
            "F. Potts": "https://media.api-sports.io/football/players/284446.png",
            "M. Fernandes": "https://media.api-sports.io/football/players/336585.png",
            "Lucas Paqueta": "https://media.api-sports.io/football/players/1646.png",
            "J. Bowen": "https://media.api-sports.io/football/players/19428.png",
            "C. Summerville": "https://media.api-sports.io/football/players/37724.png",
            # Manchester City bench (正確なURL - デバッグ実行から取得)
            "J. Trafford": "https://media.api-sports.io/football/players/162489.png",
            "N. Ake": "https://media.api-sports.io/football/players/18861.png",
            "Savinho": "https://media.api-sports.io/football/players/266657.png",
            "A. Khusanov": "https://media.api-sports.io/football/players/360114.png",
            "C. Gray": "https://media.api-sports.io/football/players/389034.png",
            "D. Mukasa": "https://media.api-sports.io/football/players/380681.png",
            "R. Lewis": "https://media.api-sports.io/football/players/284230.png",
            "S. Mfuni": "https://media.api-sports.io/football/players/382358.png",
            "R. Heskey": "https://media.api-sports.io/football/players/448969.png",
            # West Ham bench (正確なURL - デバッグ実行から取得)
            "M. Hermansen": "https://media.api-sports.io/football/players/15870.png",
            "Igor": "https://media.api-sports.io/football/players/7600.png",
            "C. Wilson": "https://media.api-sports.io/football/players/2939.png",
            "K. Mavropanos": "https://media.api-sports.io/football/players/1445.png",
            "G. Rodriguez": "https://media.api-sports.io/football/players/2476.png",
            "T. Soucek": "https://media.api-sports.io/football/players/1243.png",
            "A. Irving": "https://media.api-sports.io/football/players/68466.png",
            "M. Kante": "https://media.api-sports.io/football/players/401278.png",
            "E. Mayers": "https://media.api-sports.io/football/players/553065.png"
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
