
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    # API Keys
    RAPIDAPI_KEY: str = os.getenv("RAPIDAPI_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")
    GOOGLE_SEARCH_API_KEY: str = os.getenv("GOOGLE_SEARCH_API_KEY", "")
    
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
    TARGET_LEAGUES: List[str] = ("EPL", "CL")
    
    # S Rank Teams - Manchester City (highest priority)
    S_RANK_TEAMS: List[str] = ("Manchester City",)
    
    # A Rank Teams - Arsenal, Chelsea
    A_RANK_TEAMS: List[str] = ("Arsenal", "Chelsea")
    
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
    
    # Output
    OUTPUT_FILE: str = "daily_report.md"
    
    # Debug Mode (limit to 1 match for testing)
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Mock Mode (use hardcoded data, no API calls)
    USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "True").lower() == "true"
    
    # Dynamic Settings based on Debug Mode
    @property
    def MATCH_LIMIT(self) -> int:
        return 1 if self.DEBUG_MODE else 3
        
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
        - Normal mode: Yesterday (JST)
        - Debug mode with real API: Most recent Saturday (past)
        """
        from datetime import datetime, timedelta
        import pytz
        
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst)
        
        if self.DEBUG_MODE and not self.USE_MOCK_DATA:
            # Find most recent Saturday (0=Mon, 5=Sat)
            days_since_saturday = (now_jst.weekday() - 5) % 7
            if days_since_saturday == 0:
                # Today is Saturday, use last Saturday
                days_since_saturday = 7
            target = now_jst - timedelta(days=days_since_saturday)
            return target
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
