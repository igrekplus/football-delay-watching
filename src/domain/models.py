"""
ドメインモデル

試合データやその他のドメインオブジェクトを定義
"""

from dataclasses import dataclass
from typing import List, Optional
import re


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
    
    # Match date in local time (YYYY-MM-DD format)
    match_date_local: str = ""  # 試合開催日（現地時間）
    
    # Facts Data (populated by FactsService)
    venue: str = ""
    home_lineup: List[str] = None
    away_lineup: List[str] = None
    home_bench: List[str] = None
    away_bench: List[str] = None
    home_formation: str = ""
    away_formation: str = ""
    referee: str = "" # W-L-D
    home_recent_form: str = ""
    away_recent_form: str = ""
    
    # Player Nationalities (name -> nationality mapping)
    player_nationalities: dict = None  # {"Player Name": "England", ...}
    
    # Player Numbers (name -> jersey number mapping)
    player_numbers: dict = None  # {"Player Name": 1, ...}
    
    # Player Photos (name -> photo URL mapping)
    player_photos: dict = None  # {"Player Name": "https://...", ...}
    
    # Player Birthdates (name -> birth date mapping)
    player_birthdates: dict = None  # {"Player Name": "2000-03-06", ...}
    
    # Player Positions (name -> position mapping, for bench players)
    player_positions: dict = None  # {"Player Name": "G", ...} (G=GK, D=DF, M=MF, F=FW)
    
    # Injuries and Suspensions (structured data)
    injuries_list: list = None  # [{"name": "Player", "team": "Team", "reason": "Injury"}, ...]
    injuries_info: str = "不明"  # 負傷者・出場停止情報（フォールバック用テキスト）
    
    # Head-to-Head History
    h2h_summary: str = ""  # 過去の対戦成績サマリー（例: "5試合: Home 2勝, Draw 1, Away 2勝"）
    
    # Manager names (populated from lineups API coach data)
    home_manager: str = ""
    away_manager: str = ""
    
    # Issue #52: Team logos
    home_logo: str = ""  # ホームチームロゴURL
    away_logo: str = ""  # アウェイチームロゴURL
    
    # Issue #53: Manager photos
    home_manager_photo: str = ""  # ホーム監督画像URL
    away_manager_photo: str = ""  # アウェイ監督画像URL
    
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
        if self.player_birthdates is None: self.player_birthdates = {}
        if self.player_positions is None: self.player_positions = {}
        if self.injuries_list is None: self.injuries_list = []
    
    @staticmethod
    def _normalize_team_name(team_name: str) -> str:
        """
        チーム名をファイル名用に正規化
        - スペースを削除
        - 特殊文字を削除（英数字とハイフンのみ許可）
        """
        # スペースを削除
        normalized = team_name.replace(" ", "")
        # 特殊文字を削除（英数字とハイフンのみ許可）
        normalized = re.sub(r'[^a-zA-Z0-9\-]', '', normalized)
        return normalized
    
    def get_report_filename(self, generation_datetime: str) -> str:
        """
        レポートファイル名を生成
        
        Args:
            generation_datetime: レポート生成日時（YYYYMMDD_HHMMSS形式）
        
        Returns:
            ファイル名（拡張子なし）
            例: "2025-12-27_ManchesterCity_vs_Arsenal_20251228_072100"
        """
        home_normalized = self._normalize_team_name(self.home_team)
        away_normalized = self._normalize_team_name(self.away_team)
        
        # match_date_local が空の場合は kickoff_local から抽出を試みる
        match_date = self.match_date_local
        if not match_date and self.kickoff_local:
            # "2025-12-27 20:00 GMT" のような形式から日付部分を抽出
            match_date = self.kickoff_local.split()[0] if self.kickoff_local else ""
        
        filename = f"{match_date}_{home_normalized}_vs_{away_normalized}_{generation_datetime}"
        return filename
