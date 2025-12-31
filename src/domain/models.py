"""
ドメインモデル

試合データを保持するデータクラスを定義。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import re


@dataclass
class MatchData:
    """
    試合データを保持するデータクラス
    
    このクラスはアプリケーション全体で使用される主要なドメインモデルです。
    各サービスがこのオブジェクトを更新してデータを追加していきます。
    
    生成・更新フロー:
    1. MatchProcessor: 基本情報（id, home_team, away_team等）を設定して生成
    2. FactsService: スタメン・フォーメーション・選手情報等を追加
    3. NewsService: ニュース要約・戦術プレビュー等を追加
    4. YouTubeService: 動画情報（別途Dictで管理）
    5. ReportGenerator: レポート出力
    
    フィールドの責務:
    - 試合基本情報: id, home_team, away_team, competition, kickoff_*, rank等
    - 選手・チーム情報: *_lineup, *_bench, *_formation, player_*等
    - 追加取得情報: venue, referee, *_manager, h2h_summary等
    - LLM生成コンテンツ: news_summary, tactical_preview, *_interview等
    - エラー状態: error_status
    """
    # =========================================================================
    # 試合基本情報（MatchProcessorで設定）
    # =========================================================================
    id: str
    home_team: str
    away_team: str
    competition: str  # EPL, CL, LaLiga等
    kickoff_jst: str  # 表示用（例: "01/01 04:30"）
    kickoff_local: str  # 現地時間（例: "2025-12-27 20:00 GMT"）
    rank: str  # Absolute, S, A, or empty
    selection_reason: str = ""
    is_target: bool = False
    match_date_local: str = ""  # 試合開催日（現地時間）YYYY-MM-DD
    kickoff_at_utc: Optional[datetime] = None  # UTC datetime（計算用）
    
    # =========================================================================
    # 選手・チーム情報（FactsServiceで設定）
    # =========================================================================
    venue: str = ""
    home_lineup: List[str] = None
    away_lineup: List[str] = None
    home_bench: List[str] = None
    away_bench: List[str] = None
    home_formation: str = ""
    away_formation: str = ""
    referee: str = ""
    home_recent_form: str = ""  # 直近5試合の結果（W-L-D形式）
    away_recent_form: str = ""
    
    # 選手詳細情報（name -> value のマッピング）
    player_nationalities: dict = None  # {"Player Name": "England", ...}
    player_numbers: dict = None  # {"Player Name": 1, ...}
    player_photos: dict = None  # {"Player Name": "https://...", ...}
    player_birthdates: dict = None  # {"Player Name": "2000-03-06", ...}
    player_positions: dict = None  # {"Player Name": "G", ...} (G=GK, D=DF, M=MF, F=FW)
    player_instagram: dict = None  # {"Player Name": "https://instagram.com/...", ...}
    
    # 負傷者・出場停止情報
    injuries_list: list = None  # [{"name": "Player", "team": "Team", "reason": "Injury"}, ...]
    injuries_info: str = "不明"  # フォールバック用テキスト
    
    # 対戦成績
    h2h_summary: str = ""  # 例: "5試合: Home 2勝, Draw 1, Away 2勝"
    
    # 監督情報
    home_manager: str = ""
    away_manager: str = ""
    home_manager_photo: str = ""
    away_manager_photo: str = ""
    
    # チームロゴ
    home_logo: str = ""
    away_logo: str = ""
    
    # =========================================================================
    # LLM生成コンテンツ（NewsServiceで設定）
    # =========================================================================
    news_summary: str = ""
    tactical_preview: str = ""
    preview_url: str = ""
    home_interview: str = ""  # ホームチーム監督・選手インタビュー要約
    away_interview: str = ""  # アウェイチーム監督・選手インタビュー要約
    
    # =========================================================================
    # エラー状態
    # =========================================================================
    error_status: str = "Normal"  # Normal, E1, E2, E3
    
    def __post_init__(self):
        """リストや辞書フィールドを初期化"""
        if self.home_lineup is None: self.home_lineup = []
        if self.away_lineup is None: self.away_lineup = []
        if self.home_bench is None: self.home_bench = []
        if self.away_bench is None: self.away_bench = []
        if self.player_nationalities is None: self.player_nationalities = {}
        if self.player_numbers is None: self.player_numbers = {}
        if self.player_photos is None: self.player_photos = {}
        if self.player_birthdates is None: self.player_birthdates = {}
        if self.player_positions is None: self.player_positions = {}
        if self.player_instagram is None: self.player_instagram = {}
        if self.injuries_list is None: self.injuries_list = []
    
    @staticmethod
    def _normalize_team_name(team_name: str) -> str:
        """
        チーム名をファイル名用に正規化
        - スペースを削除
        - 特殊文字を削除（英数字とハイフンのみ許可）
        """
        normalized = team_name.replace(" ", "")
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
            match_date = self.kickoff_local.split()[0] if self.kickoff_local else ""
        
        filename = f"{match_date}_{home_normalized}_vs_{away_normalized}_{generation_datetime}"
        return filename
