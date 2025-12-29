from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import pytz

from config import config
from src.domain.models import MatchData
from src.clients.api_football_client import ApiFootballClient
from src.domain.match_ranker import MatchRanker
from src.domain.match_selector import MatchSelector
from src.mock_provider import MockProvider

logger = logging.getLogger(__name__)

class MatchProcessor:
    """
    Orchestrates the retrieval, ranking, and selection of matches.
    """
    def __init__(self):
        self.client = ApiFootballClient()
        self.ranker = MatchRanker()
        self.selector = MatchSelector()

    def run(self) -> List[MatchData]:
        matches = self.extract_matches()
        
        # Calculate Rank for all matches
        for m in matches:
            self.ranker.assign_rank(m)
            
        selected_matches = self.selector.select(matches)
        return selected_matches

    def extract_matches(self) -> List[MatchData]:
        if config.USE_MOCK_DATA:
            return MockProvider.get_matches()
        else:
            return self._fetch_matches_from_api()

    def _fetch_matches_from_api(self) -> List[MatchData]:
        """Fetch and parse matches from API-Football."""
        matches = []
        target_date = config.TARGET_DATE
        date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"Fetching matches for date: {date_str}")
        
        # Calculate Season
        season_year = target_date.year if target_date.month >= 6 else target_date.year - 1
        
        target_league_ids = config.LEAGUE_IDS
        
        for league_name, league_id in target_league_ids.items():
            if league_name not in config.TARGET_LEAGUES:
                continue
                
            data = self.client.get_fixtures(league_id, season_year, date_str)
            
            # Parse response
            for item in data.get('response', []):
                match_data = self._parse_match_data(item, league_name, target_date)
                if match_data:
                    matches.append(match_data)
                    
        return matches

    def _parse_match_data(self, item: Dict[str, Any], league_name: str, target_date: datetime) -> Optional[MatchData]:
        """Parses a single match item and applies time window filtering."""
        fixture = item['fixture']
        teams = item['teams']
        
        # Check status (Skip Cancelled/Postponed)
        status = fixture['status']['short']
        if status in ["CANC", "PST", "ABD", "AWD", "WO"]:
            return None
        
        # Timezone conversion
        jst = pytz.timezone('Asia/Tokyo')
        match_date_utc = datetime.fromisoformat(fixture['date'].replace("Z", "+00:00"))
        match_date_jst = match_date_utc.astimezone(jst)
        match_date_local = match_date_utc # Placeholder for local time (could be improved)
        
        # Time window filter
        if not self._is_within_time_window(match_date_jst, target_date, jst):
            return None
        
        # Extract Venue
        venue_name = fixture.get('venue', {}).get('name', 'Unknown Venue')
        venue_city = fixture.get('venue', {}).get('city', '')
        venue_full = f"{venue_name}, {venue_city}" if venue_city else venue_name

        # Japanese Weekday
        weekday_ja = ['月', '火', '水', '木', '金', '土', '日'][match_date_jst.weekday()]
        
        # Team Logos
        home_logo_url = teams['home'].get('logo', '')
        away_logo_url = teams['away'].get('logo', '')
        
        return MatchData(
            id=str(fixture['id']),
            home_team=teams['home']['name'],
            away_team=teams['away']['name'],
            competition=league_name,
            kickoff_jst=match_date_jst.strftime(f'%Y/%m/%d({weekday_ja}) %H:%M JST'),
            kickoff_local=match_date_local.strftime('%Y-%m-%d %H:%M Local'),
            rank="None", # Calculated later
            venue=venue_full,
            referee=fixture.get('referee', 'Unknown'),
            home_logo=home_logo_url,
            away_logo=away_logo_url,
            kickoff_at_utc=match_date_utc,
        )

    def _is_within_time_window(self, match_date_jst: datetime, target_date: datetime, tz) -> bool:
        """Checks if the match is within the target time window."""
        # Standard Window: D-1 07:00 JST to D 07:00 JST
        now_jst = datetime.now(tz)
        
        # By default, use current time for window calculation reference in production behavior
        # But for 'target_date' logic (debug mode), we use target_date.
        
        if config.DEBUG_MODE and not config.USE_MOCK_DATA:
            target_next_day = target_date + timedelta(days=1)
            # Ensure timezone awareness
            # target_date is already aware (JST) from config
            if target_next_day.tzinfo is None:
                window_end = tz.localize(target_next_day.replace(hour=7, minute=0, second=0, microsecond=0))
            else:
                window_end = target_next_day.replace(hour=7, minute=0, second=0, microsecond=0)
        else:
             # Original logic: window_end = now_jst.replace(hour=7, ...)
             # This means "Today at 7am".
             # If run at 8am, window ends at 7am (1 hour ago).
             # It effectively looks for matches in the *previous* 24h cycle ending this morning.
             window_end = now_jst.replace(hour=7, minute=0, second=0, microsecond=0)
             
        window_start = window_end - timedelta(days=1)
        
        return window_start <= match_date_jst < window_end
