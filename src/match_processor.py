from typing import List, Optional
from config import config
from src.domain.models import MatchData
import logging

logger = logging.getLogger(__name__)

class MatchProcessor:
    def __init__(self):
        pass

    def run(self) -> List[MatchData]:
        matches = self.extract_matches()
        selected_matches = self.select_matches(matches)
        return selected_matches

    def extract_matches(self) -> List[MatchData]:
        if config.USE_MOCK_DATA:
            return self._get_mock_matches()
        else:
            return self._fetch_matches_from_api()

    def _fetch_matches_from_api(self) -> List[MatchData]:
        # import requests # Removed requests import
        from src.clients.cache import get_with_cache
        from datetime import datetime, timedelta
        import pytz

        # API-Football logic
        # Targeted Leagues: 39 (Premier League), 2 (Champions League)
        # Dates: Yesterday
        
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            "x-apisports-key": config.API_FOOTBALL_KEY
        }
        
        # Determine Target Date
        # Normal mode: Yesterday (JST)
        # Debug mode with real API: Most recent Saturday
        target_date = config.TARGET_DATE
        date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"Fetching matches for date: {date_str}")
        
        matches = []
        target_league_ids = config.LEAGUE_IDS
        
        # Calculate Season based on target_date
        # Approx: If Month >= 8 (Aug), Season = Year. Else Season = Year-1.
        season_year = target_date.year if target_date.month >= 6 else target_date.year - 1
        
        for league_name, league_id in target_league_ids.items():
            if league_name not in config.TARGET_LEAGUES:
                continue
                
            querystring = {
                "date": date_str,
                "league": league_id,
                "season": str(season_year)
            }
            
            try:
                response = get_with_cache(url, headers=headers, params=querystring)
                
                # Capture Rate Limit Info
                if "x-ratelimit-requests-remaining" in response.headers:
                    remaining = response.headers["x-ratelimit-requests-remaining"]
                    limit = response.headers.get("x-ratelimit-requests-limit", "Unknown")
                    config.QUOTA_INFO["API-Football"] = f"Remaining: {remaining} / Limit: {limit} (requests/day)"
                    logger.info(f"API-Football Quota: {remaining}/{limit}")

                data = response.json()
                
                # Parse response
                for item in data.get('response', []):
                    fixture = item['fixture']
                    teams = item['teams']
                    league = item['league']
                    
                    # Check status (Finished only?)
                    # For now get all and let logic filter or assumed finished if running next day
                    status = fixture['status']['short']
                    if status not in ["FT", "AET", "PEN"]:
                        continue # Skip non-finished matches
                    
                    # Convert match time to JST string (from UTC timestamp or string)
                    jst = pytz.timezone('Asia/Tokyo')
                    match_date_utc = datetime.fromisoformat(fixture['date'].replace("Z", "+00:00"))
                    match_date_jst = match_date_utc.astimezone(jst)
                    match_date_local = match_date_utc # Simplify for now, ideally use venue timezone
                    
                    # Time window filter: D-1 07:00 JST to D 07:00 JST
                    # (matches that kicked off within this 24-hour window)
                    now_jst = datetime.now(jst)
                    window_end = now_jst.replace(hour=7, minute=0, second=0, microsecond=0)
                    window_start = window_end - timedelta(days=1)
                    
                    # For debug mode, adjust window based on target_date
                    if config.DEBUG_MODE and not config.USE_MOCK_DATA:
                        # Use target_date + 1 day at 07:00 as window_end
                        target_next_day = target_date + timedelta(days=1)
                        window_end = target_next_day.replace(hour=7, minute=0, second=0, microsecond=0)
                        window_start = window_end - timedelta(days=1)
                    
                    if not (window_start <= match_date_jst < window_end):
                        continue  # Skip matches outside the time window
                    
                    # Extract Venue
                    venue_name = fixture.get('venue', {}).get('name', 'Unknown Venue')
                    venue_city = fixture.get('venue', {}).get('city', '')
                    venue_full = f"{venue_name}, {venue_city}" if venue_city else venue_name

                    matches.append(MatchData(
                        id=str(fixture['id']),
                        home_team=teams['home']['name'],
                        away_team=teams['away']['name'],
                        competition=league_name,
                        kickoff_jst=match_date_jst.strftime('%Y/%m/%d %H:%M JST'),
                        kickoff_local=match_date_local.strftime('%Y-%m-%d %H:%M Local'), # TODO: accurate local time
                        rank="None", # Rank calculated later
                        venue=venue_full,
                        referee=fixture.get('referee', 'Unknown')
                    ))
            
            except Exception as e:
                logger.error(f"Error fetching matches for {league_name}: {e}")
                
        # Calculate Rank
        for m in matches:
            self._assign_rank(m)
            
        return matches

    def _assign_rank(self, match: MatchData):
        # 1. S Rank - Manchester City (highest priority)
        if any(t in match.home_team or t in match.away_team for t in config.S_RANK_TEAMS):
            match.rank = "S"
            logger.info(f"Assigned S to {match.home_team} vs {match.away_team}")
            return
        
        # 2. A Rank - Arsenal, Chelsea
        if any(t in match.home_team or t in match.away_team for t in config.A_RANK_TEAMS):
            match.rank = "A"
            logger.info(f"Assigned A to {match.home_team} vs {match.away_team}")
            return
        
        # 3. A Rank - Japanese player starting
        all_players = match.home_lineup + match.away_lineup
        if any(jp in player for jp in config.JAPANESE_PLAYERS for player in all_players):
            match.rank = "A"
            logger.info(f"Assigned A (Japanese player) to {match.home_team} vs {match.away_team}")
            return
        
        # 4. No special rank
        match.rank = "None"
    
    def _get_mock_matches(self) -> List[MatchData]:
        # Mock data based on real match: Manchester City vs West Ham (2025-12-21)
        return [
            MatchData(
                id="1379135", home_team="Manchester City", away_team="West Ham",
                competition="EPL", kickoff_jst="2025/12/21 00:00 JST", kickoff_local="2025-12-20 15:00 Local",
                rank="S", venue="Etihad Stadium, Manchester", referee="Paul Tierney, England"
            ),
            MatchData(
                id="m2", home_team="Newcastle", away_team="Chelsea",
                competition="EPL", kickoff_jst="2025/12/21 00:00 JST", kickoff_local="2025-12-20 15:00 GMT",
                rank="A"
            ),
            MatchData(
                id="m3", home_team="Everton", away_team="Arsenal",
                competition="EPL", kickoff_jst="2025/12/21 00:00 JST", kickoff_local="2025-12-20 15:00 GMT",
                rank="A"
            ),
            MatchData(
                id="m4", home_team="Brighton", away_team="Sunderland",
                competition="EPL", kickoff_jst="2025/12/21 00:00 JST", kickoff_local="2025-12-20 15:00 GMT",
                rank="None"
            )
        ]

    def select_matches(self, matches: List[MatchData]) -> List[MatchData]:
        """
        試合の選定ロジック:
        1. まず rank != None を優先順位で選出
        2. 選出数が MATCH_LIMIT 未満なら、rank == None で補充（フィラー）
        3. 上限は MATCH_LIMIT
        """
        
        rank_order = {"Absolute": 0, "S": 1, "A": 2, "None": 3}
        
        # Sort logic
        def sort_key(m: MatchData):
            r_score = rank_order.get(m.rank, 99)
            # Competition priority: CL > LALIGA > EPL > COPA > FA > EFL
            comp_priority = {"CL": 0, "LALIGA": 1, "EPL": 2, "COPA": 3, "FA": 4, "EFL": 5}
            comp_score = comp_priority.get(m.competition, 99)
            return (r_score, comp_score)

        sorted_matches = sorted(matches, key=sort_key)
        
        limit = config.MATCH_LIMIT
        
        # Step 1: rank != None の試合を選出
        high_rank_matches = [m for m in sorted_matches if m.rank != "None"]
        low_rank_matches = [m for m in sorted_matches if m.rank == "None"]
        
        selected_count = 0
        result = []
        
        # 高ランク試合を優先的に選出
        for match in high_rank_matches:
            if selected_count < limit:
                match.is_target = True
                match.selection_reason = None  # Clear any previous reason
                selected_count += 1
            else:
                match.is_target = False
                match.selection_reason = "Out of quota"
            result.append(match)
        
        # Step 2: 残り枠をLowランクで補充（フィラー）
        for match in low_rank_matches:
            if selected_count < limit:
                match.is_target = True
                match.selection_reason = "Included as filler"
                logger.info(f"Including low-rank match as filler: {match.home_team} vs {match.away_team}")
                selected_count += 1
            else:
                match.is_target = False
                match.selection_reason = "Low rank"
            result.append(match)
        
        logger.info(f"Selected {selected_count} matches (limit: {limit})")
        return result
