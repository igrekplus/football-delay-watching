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
        from src.clients.caching_http_client import create_caching_client
        from datetime import datetime, timedelta
        import pytz

        # HTTPクライアント初期化
        http_client = create_caching_client()
        
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
                response = http_client.get(url, headers=headers, params=querystring)
                
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
                    
                    # Check status
                    # 試合前（NS）も含めて処理（プレビュー目的のため）
                    # status = fixture['status']['short']
                    # キャンセル・延期のみスキップ
                    status = fixture['status']['short']
                    if status in ["CANC", "PST", "ABD", "AWD", "WO"]:
                        continue  # Skip cancelled/postponed matches
                    
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

                    # Issue #55: 日本語曜日を追加
                    weekday_ja = ['月', '火', '水', '木', '金', '土', '日'][match_date_jst.weekday()]
                    
                    # Issue #52: チームロゴURLを取得
                    home_logo_url = teams['home'].get('logo', '')
                    away_logo_url = teams['away'].get('logo', '')
                    
                    matches.append(MatchData(
                        id=str(fixture['id']),
                        home_team=teams['home']['name'],
                        away_team=teams['away']['name'],
                        competition=league_name,
                        kickoff_jst=match_date_jst.strftime(f'%Y/%m/%d({weekday_ja}) %H:%M JST'),
                        kickoff_local=match_date_local.strftime('%Y-%m-%d %H:%M Local'), # TODO: accurate local time
                        rank="None", # Rank calculated later
                        venue=venue_full,
                        referee=fixture.get('referee', 'Unknown'),
                        home_logo=home_logo_url,
                        away_logo=away_logo_url,
                        # Issue #70: timezone-aware UTC datetime
                        kickoff_at_utc=match_date_utc,
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
        """モック試合データを取得"""
        from src.mock_provider import MockProvider
        return MockProvider.get_matches()

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
