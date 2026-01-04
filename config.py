
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    # API Keys
    API_FOOTBALL_KEY: str = os.getenv("API_FOOTBALL_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # Gmail
    NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")
    GMAIL_ENABLED = os.getenv("GMAIL_ENABLED", "False").lower() == "true"
    
    # API Cache (explicit override via env var)
    _USE_API_CACHE_OVERRIDE = os.getenv("USE_API_CACHE")
    
    @property
    def USE_API_CACHE(self) -> bool:
        """
        API Cache setting:
        - If USE_API_CACHE env var is set, use that value
        - Otherwise, enable cache in Debug mode (real API) by default
        - Disable in production and mock mode
        """
        if self._USE_API_CACHE_OVERRIDE is not None:
            return self._USE_API_CACHE_OVERRIDE.lower() == "true"
        # Default: enable cache in debug mode with real API
        return self.DEBUG_MODE and not self.USE_MOCK_DATA

    # Target Leagues
    TARGET_LEAGUES: List[str] = ("EPL", "CL", "LALIGA", "FA", "COPA", "EFL")
    
    # League ID Mapping for API-Football
    LEAGUE_IDS = {
        "EPL": 39,      # Premier League
        "CL": 2,        # Champions League
        "LALIGA": 140,  # La Liga
        "FA": 45,       # FA Cup
        "COPA": 143,    # Copa del Rey
        "EFL": 48,      # EFL Cup (Carabao Cup)
    }
    
    # S Rank Teams - Manchester City (highest priority)
    S_RANK_TEAMS: List[str] = ("Manchester City",)
    
    # A Rank Teams - Arsenal, Chelsea, and other popular clubs
    A_RANK_TEAMS: List[str] = (
        "Arsenal", "Chelsea", "Brighton", "Manchester United", "Liverpool", 
        "Tottenham", "Leeds United", "Barcelona", "Real Madrid", 
        "Atletico Madrid", "Real Sociedad"
    )
    
    # CL Big Teams (S Rank)
    CL_BIG_TEAMS: List[str] = (
        "Real Madrid", "Barcelona", "Bayern Munich", "Paris Saint Germain",
        "Inter", "AC Milan", "Juventus", "Manchester City", 
        "Atletico Madrid", "Arsenal","Chelsea","Liverpool"
    )
    
    # Japanese Players for A Rank detection
    JAPANESE_PLAYERS: List[str] = (
        "Mitoma", "Tomiyasu", "Endo", "Kubo", "Kamada", "Maeda", "Furuhashi",
        "Tanaka", "Doan", "Ito", "Minamino", "Ueda"
    )
    
    # Cache Warming Settings (2024-25 Season, Dec 2024 standings)
    # EPL Top 10 Teams with their API-Football team IDs
    EPL_CACHE_TEAMS: List[tuple] = (
        (40, "Liverpool"),
        (49, "Chelsea"),
        (42, "Arsenal"),
        (65, "Nottingham Forest"),
        (51, "Brighton"),
        (50, "Manchester City"),
        (35, "Bournemouth"),
        (34, "Newcastle"),
        (66, "Aston Villa"),
        (36, "Fulham"),
    )
    
    # CL Top Teams with their API-Football team IDs (12 teams including big clubs)
    CL_CACHE_TEAMS: List[tuple] = (
        (40, "Liverpool"),
        (529, "Barcelona"),
        (42, "Arsenal"),
        (505, "Inter"),
        (168, "Bayer Leverkusen"),
        (530, "Atletico Madrid"),
        (489, "AC Milan"),
        (499, "Atalanta"),
        (91, "Monaco"),
        (228, "Sporting CP"),
        (157, "Bayern Munich"),
        (165, "Borussia Dortmund"),
        (541, "Real Madrid"),
    )
    
    # Minimum remaining quota to start cache warming
    CACHE_WARMING_QUOTA_THRESHOLD: int = 30
    
    # Output
    OUTPUT_FILE: str = "daily_report.md"
    
    # Debug Mode (limit to 1 match for testing)
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Mock Mode (use hardcoded data, no API calls)
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "True").lower() == "true"
    
    # Dynamic Settings based on Debug Mode
    @property
    def MATCH_LIMIT(self) -> int:
        return 1 if self.DEBUG_MODE else 5
        
    @property
    def NEWS_SEARCH_LIMIT(self) -> int:
        return 3 if self.DEBUG_MODE else 10
        
    @property
    def OUTPUT_DIR(self) -> str:
        """
        Output directory based on mode:
        - Mock mode: reports_mock/
        - Debug mode (real API): reports_debug/
        - Production mode: reports/
        """
        if self.USE_MOCK_DATA:
            return "reports_mock"
        elif self.DEBUG_MODE:
            return "reports_debug"
        else:
            return "reports"
    
    @property
    def TARGET_DATE(self) -> 'datetime':
        """
        Returns the target date for match extraction.
        - Env var TARGET_DATE (YYYY-MM-DD): Returns that date at 07:00 JST
        - Normal mode: Yesterday (JST)
        - Debug mode with real API (default): Today (Now)
        """
        from datetime import datetime, timedelta
        import pytz
        
        jst = pytz.timezone('Asia/Tokyo')
        
        # Override via environment variable
        env_target_date = os.getenv("TARGET_DATE")
        if env_target_date:
            try:
                # Parse YYYY-MM-DD and set time to 07:00 JST (simulating report execution time)
                # match_processor will use this to calculate [TARGET_DATE-1 07:00 ~ TARGET_DATE 07:00]
                d = datetime.strptime(env_target_date, "%Y-%m-%d")
                return jst.localize(d.replace(hour=7, minute=0, second=0, microsecond=0))
            except ValueError:
                pass

        now_jst = datetime.now(jst)
        
        if self.DEBUG_MODE and not self.USE_MOCK_DATA:
            # Debug mode: 過去24時間以内の最近キックオフ試合を対象
            # TARGET_DATEは現在時刻を返し、match_processorで過去24時間を検索
            return now_jst
        else:
            # Normal mode: yesterday
            return now_jst - timedelta(days=1)

    # Mock Data Flags (Default to False if keys are present, else True)
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "True").lower() == "true"

    # Error Levels
    ERROR_CRITICAL: str = "E1"
    ERROR_PARTIAL: str = "E2"
    ERROR_MINOR: str = "E3"
    
    # News Filtering
    NEWS_MIN_CHARS: int = 600
    NEWS_MAX_CHARS: int = 1000

    # Runtime Info (Not saved in env)
    QUOTA_INFO = {}

config = Config()
