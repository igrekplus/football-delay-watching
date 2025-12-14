
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
    
    # Debug Mode
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Dynamic Settings based on Debug Mode
    @property
    def MATCH_LIMIT(self) -> int:
        return 1 if self.DEBUG_MODE else 3
        
    @property
    def NEWS_SEARCH_LIMIT(self) -> int:
        return 3 if self.DEBUG_MODE else 10
        
    @property
    def OUTPUT_DIR(self) -> str:
        return "reports_debug" if self.DEBUG_MODE else "reports"
    
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
