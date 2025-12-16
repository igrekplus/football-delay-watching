"""
ドメインモデル

試合データやその他のドメインオブジェクトを定義
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MatchData:
    """試合データを保持するデータクラス"""
    id: str
    home_team: str
    away_team: str
    competition: str  # EPL or CL
    kickoff_jst: str
    kickoff_local: str
    rank: str  # Absolute, S, A, or None
    selection_reason: str = ""
    is_target: bool = False
    
    # Facts Data (populated by FactsService)
    venue: str = ""
    home_lineup: List[str] = None
    away_lineup: List[str] = None
    home_bench: List[str] = None
    away_bench: List[str] = None
    home_formation: str = ""
    away_formation: str = ""
    referee: str = ""
    home_recent_form: str = "" # W-L-D
    away_recent_form: str = ""
    
    # Player Nationalities (name -> nationality mapping)
    player_nationalities: dict = None  # {"Player Name": "England", ...}
    
    # Player Numbers (name -> jersey number mapping)
    player_numbers: dict = None  # {"Player Name": 1, ...}
    
    # Player Photos (name -> photo URL mapping)
    player_photos: dict = None  # {"Player Name": "https://...", ...}
    
    # Injuries and Suspensions
    injuries_info: str = "不明"  # 負傷者・出場停止情報
    
    # Head-to-Head History
    h2h_summary: str = ""  # 過去の対戦成績サマリー（例: "5試合: Home 2勝, Draw 1, Away 2勝"）
    
    # Generated Content (NewsService)
    news_summary: str = ""
    tactical_preview: str = ""
    preview_url: str = ""
    home_interview: str = ""  # ホームチーム監督・選手インタビュー要約
    away_interview: str = ""  # アウェイチーム監督・選手インタビュー要約
    
    # Error Status
    error_status: str = "Normal" # Normal, E1, E2, E3
    
    def __post_init__(self):
        if self.home_lineup is None: self.home_lineup = []
        if self.away_lineup is None: self.away_lineup = []
        if self.home_bench is None: self.home_bench = []
        if self.away_bench is None: self.away_bench = []
        if self.player_nationalities is None: self.player_nationalities = {}
        if self.player_numbers is None: self.player_numbers = {}
        if self.player_photos is None: self.player_photos = {}
