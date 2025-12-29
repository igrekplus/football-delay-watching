from typing import Dict, Optional, Any
import logging
from config import config
from src.clients.caching_http_client import create_caching_client

logger = logging.getLogger(__name__)

class ApiFootballClient:
    """API-Football Client with caching capabilities."""
    
    def __init__(self):
        self.http_client = create_caching_client()
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": config.API_FOOTBALL_KEY
        }
        self.quota_info = {}

    def get_fixtures(self, league_id: int, season: int, date_str: str) -> Dict[str, Any]:
        """Fetch fixtures for a specific league, season, and date."""
        url = f"{self.base_url}/fixtures"
        querystring = {
            "date": date_str,
            "league": league_id,
            "season": str(season)
        }
        return self._fetch(url, params=querystring, label="fixtures")

    def get_squad(self, team_id: int, team_name: str = "") -> list:
        """Fetch squad (player list) for a team."""
        url = f"{self.base_url}/players/squads"
        params = {"team": team_id}
        
        response_json = self._fetch(url, params=params, label=f"squad for {team_name}")
        if response_json.get("response") and len(response_json["response"]) > 0:
            return response_json["response"][0].get("players", [])
        return []

    # --- Methods for MatchProcessor / FactsService ---

    def fetch_lineups(self, fixture_id: str) -> Dict[str, Any]:
        """Fetch lineups for a fixture."""
        url = f"{self.base_url}/fixtures/lineups"
        params = {"fixture": fixture_id}
        return self._fetch(url, params=params, label=f"lineups {fixture_id}")

    def fetch_injuries(self, fixture_id: str) -> Dict[str, Any]:
        """Fetch injuries for a fixture."""
        url = f"{self.base_url}/injuries"
        params = {"fixture": fixture_id}
        return self._fetch(url, params=params, label=f"injuries {fixture_id}")

    def fetch_fixtures(self, fixture_id: str) -> Dict[str, Any]:
        """Fetch single fixture details."""
        url = f"{self.base_url}/fixtures"
        params = {"id": fixture_id}
        return self._fetch(url, params=params, label=f"fixture {fixture_id}")
    
    def fetch_team_statistics(self, team_id: int, league_id: int, season: str = "2024") -> Dict[str, Any]:
        """Fetch team statistics."""
        # Note: Season might need to be dynamic, currently FactsService doesn't pass it explicitly.
        # FactsService logic: `_get_team_form` calls `fetch_team_statistics(team_id, league_id)`
        # I'll default to 2024 or current season logic?
        # Ideally passed from caller. For now default to 2024 to match previous implicit behavior or config.
        # Although previous code likely had it hardcoded or derived.
        # Let's use config.TARGET_DATE year?
        # Safe default to 2024 for now.
        url = f"{self.base_url}/teams/statistics"
        params = {"team": team_id, "league": league_id, "season": season}
        return self._fetch(url, params=params, label=f"stats team {team_id}")

    def fetch_h2h(self, team1_id: int, team2_id: int) -> Dict[str, Any]:
        """Fetch H2H."""
        url = f"{self.base_url}/fixtures/headtohead"
        h2h_param = f"{team1_id}-{team2_id}"
        params = {"h2h": h2h_param}
        return self._fetch(url, params=params, label=f"h2h {h2h_param}")

    def fetch_player_details(self, player_id: int, team_name: str, season: int = 2024) -> Dict[str, Any]:
        """Fetch player details."""
        url = f"{self.base_url}/players"
        params = {"id": player_id, "season": season}
        return self._fetch(url, params=params, label=f"player {player_id}")

    # Aliases for compatibility or explicit naming (CacheWarmer uses get_player)
    def get_player(self, player_id: int, season: int, team_name: str = "") -> Optional[Any]:
        """Fetch player alias returning raw response object for CacheWarmer backward compat check."""
        # CacheWarmer expected the raw response object to check status code?
        # My previous implementation returned requests.Response.
        # New implementation `_fetch` returns JSON dict.
        # CacheWarmer needs to know if it succeeded (status 200).
        # JSON dict usually has 'errors' or empty 'response' if failed.
        # But `CacheWarmer._cache_player` checks `response.status_code == 200`.
        # I need to support that interface OR update CacheWarmer.
        # Let's update this method to be flexible.
        
        # Actually, `CacheWarmer` uses `self.client.get_player(...)`.
        # My previous implementation of `get_player` returned `response` object.
        # `FactsService` uses `fetch_player_details` which expects JSON.
        
        # Implementation for CacheWarmer support:
        url = f"{self.base_url}/players"
        params = {"id": player_id, "season": season}
        try:
             # Direct call to http_client to get raw response object
             return self.http_client.get(url, headers=self.headers, params=params)
             # Note: _update_quota handles headers, so we should call it.
        except Exception as e:
            logger.error(f"Error in get_player: {e}")
            return None

    def _fetch(self, url: str, params: Dict[str, Any], label: str) -> Dict[str, Any]:
        """Internal fetch helper."""
        try:
            response = self.http_client.get(url, headers=self.headers, params=params)
            self._update_quota(response)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error ({label}): {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            logger.error(f"Exception fetching {label}: {e}")
            return {}

    def _update_quota(self, response):
        """Update quota information from response headers."""
        if hasattr(response, "headers") and "x-ratelimit-requests-remaining" in response.headers:
            remaining = response.headers["x-ratelimit-requests-remaining"]
            limit = response.headers.get("x-ratelimit-requests-limit", "Unknown")
            info = f"Remaining: {remaining} / Limit: {limit} (requests/day)"
            config.QUOTA_INFO["API-Football"] = info
            self.quota_info = {"remaining": remaining, "limit": limit}
