"""
ドメインモデル

試合データを保持するデータクラスを定義。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import re


# =============================================================================
# 責務分離モデル（Issue #100）
# =============================================================================

@dataclass
class MatchCore:
    """
    試合の基本情報（MatchProcessorで生成）
    
    不変データ: 試合IDやチーム名など、取得後に変更されない情報
    """
    id: str
    home_team: str
    away_team: str
    competition: str  # EPL, CL, LaLiga等
    kickoff_jst: str  # 表示用（例: "2025/01/01(水) 04:30 JST"）
    kickoff_local: str  # 現地時間（例: "2025-12-27 20:00 Local"）
    rank: str = ""  # Absolute, S, A, or empty
    selection_reason: str = ""
    is_target: bool = False
    match_date_local: str = ""  # 試合開催日（現地時間）YYYY-MM-DD
    kickoff_at_utc: Optional[datetime] = None  # UTC datetime（計算用）
    competition_logo: str = ""  # 大会ロゴURL
    venue: str = ""
    referee: str = ""
    home_logo: str = ""
    away_logo: str = ""
    competition_logo: str = ""  # 大会ロゴURL (Issue #116)


@dataclass
class MatchFacts:
    """
    API取得データ（FactsServiceで生成）
    
    試合に関するファクト情報: スタメン、フォーメーション、選手情報、怪我人情報等
    """
    # スタメン・ベンチ
    home_lineup: List[str] = field(default_factory=list)
    away_lineup: List[str] = field(default_factory=list)
    home_bench: List[str] = field(default_factory=list)
    away_bench: List[str] = field(default_factory=list)
    home_formation: str = ""
    away_formation: str = ""
    
    
    # 直近5試合詳細 (Issue #132)
    home_recent_form_details: List[Dict] = field(default_factory=list)
    away_recent_form_details: List[Dict] = field(default_factory=list)
    # [{"date": "2026-01-01", "opponent": "Arsenal", "competition": "Premier League", 
    #   "round": "Matchday 19", "score": "2-1", "result": "W"}, ...]
    
    # 選手詳細情報
    player_nationalities: Dict[str, str] = field(default_factory=dict)
    player_numbers: Dict[str, int] = field(default_factory=dict)
    player_photos: Dict[str, str] = field(default_factory=dict)
    player_birthdates: Dict[str, str] = field(default_factory=dict)
    player_positions: Dict[str, str] = field(default_factory=dict)
    player_instagram: Dict[str, str] = field(default_factory=dict)
    
    # 負傷者情報
    injuries_list: List[Dict] = field(default_factory=list)
    injuries_info: str = "不明"
    
    # 対戦成績
    h2h_summary: str = ""
    h2h_details: List[Dict] = field(default_factory=list)
    # [{"date": "2024-01-15", "competition": "Premier League", "home": "Liverpool", "away": "Man City", "score": "1-1", "winner": "draw"}, ...]
    
    # 同国対決（Issue #39）
    same_country_matchups: List[Dict] = field(default_factory=list)
    # [{"country": "Japan", "home_players": ["三笘薫"], "away_players": ["冨安健洋"]}, ...]
    same_country_text: str = ""  # Geminiによる関係性・小ネタテキスト
    
    # 古巣対決（Issue #20）
    former_club_trivia: str = ""  # Gemini Groundingで生成したテキスト
    
    # 監督情報
    home_manager: str = ""
    away_manager: str = ""
    home_manager_photo: str = ""
    away_manager_photo: str = ""



@dataclass
class MatchPreview:
    """
    LLM生成データ（NewsServiceで生成）
    
    Gemini APIで生成されるプレビュー情報
    """
    news_summary: str = ""
    tactical_preview: str = ""
    preview_url: str = ""
    home_interview: str = ""
    away_interview: str = ""


@dataclass
class MatchMedia:
    """
    メディアデータ（ReportGenerator/YouTubeServiceで生成）
    
    フォーメーション画像やYouTube動画リスト
    """
    formation_image_path: str = ""
    youtube_videos: Dict[str, List[Dict]] = field(default_factory=dict)


@dataclass
class MatchAggregate:
    """
    統合コンテナ（各サービスで段階的に構築）
    
    データフロー:
    - MatchProcessor: core を生成
    - FactsService: facts を生成（core を参照）
    - NewsService: preview を生成（core, facts を参照）
    - YouTubeService/ReportGenerator: media を生成
    
    後方互換性のため、MatchDataと同じプロパティアクセスをサポート
    """
    core: MatchCore
    facts: MatchFacts = field(default_factory=MatchFacts)
    preview: MatchPreview = field(default_factory=MatchPreview)
    media: MatchMedia = field(default_factory=MatchMedia)
    error_status: str = "Normal"  # Normal, E1, E2, E3
    
    # =========================================================================
    # 後方互換プロパティ（既存コードからのアクセスをサポート）
    # =========================================================================
    
    # --- Core プロパティ ---
    @property
    def id(self) -> str:
        return self.core.id
    
    @id.setter
    def id(self, value: str):
        self.core.id = value
    
    @property
    def home_team(self) -> str:
        return self.core.home_team
    
    @home_team.setter
    def home_team(self, value: str):
        self.core.home_team = value
    
    @property
    def away_team(self) -> str:
        return self.core.away_team
    
    @away_team.setter
    def away_team(self, value: str):
        self.core.away_team = value
    
    @property
    def competition(self) -> str:
        return self.core.competition
    
    @competition.setter
    def competition(self, value: str):
        self.core.competition = value
    
    @property
    def kickoff_jst(self) -> str:
        return self.core.kickoff_jst
    
    @kickoff_jst.setter
    def kickoff_jst(self, value: str):
        self.core.kickoff_jst = value
    
    @property
    def kickoff_local(self) -> str:
        return self.core.kickoff_local
    
    @kickoff_local.setter
    def kickoff_local(self, value: str):
        self.core.kickoff_local = value
    
    @property
    def rank(self) -> str:
        return self.core.rank
    
    @rank.setter
    def rank(self, value: str):
        self.core.rank = value
    
    @property
    def selection_reason(self) -> str:
        return self.core.selection_reason
    
    @selection_reason.setter
    def selection_reason(self, value: str):
        self.core.selection_reason = value
    
    @property
    def is_target(self) -> bool:
        return self.core.is_target
    
    @is_target.setter
    def is_target(self, value: bool):
        self.core.is_target = value
    
    @property
    def match_date_local(self) -> str:
        return self.core.match_date_local
    
    @match_date_local.setter
    def match_date_local(self, value: str):
        self.core.match_date_local = value
    
    @property
    def kickoff_at_utc(self) -> Optional[datetime]:
        return self.core.kickoff_at_utc
    
    @kickoff_at_utc.setter
    def kickoff_at_utc(self, value: Optional[datetime]):
        self.core.kickoff_at_utc = value
    
    @property
    def venue(self) -> str:
        return self.core.venue
    
    @venue.setter
    def venue(self, value: str):
        self.core.venue = value
    
    @property
    def referee(self) -> str:
        return self.core.referee
    
    @referee.setter
    def referee(self, value: str):
        self.core.referee = value
    
    @property
    def home_logo(self) -> str:
        return self.core.home_logo
    
    @home_logo.setter
    def home_logo(self, value: str):
        self.core.home_logo = value
    
    @property
    def away_logo(self) -> str:
        return self.core.away_logo
    
    @away_logo.setter
    def away_logo(self, value: str):
        self.core.away_logo = value
    
    @property
    def competition_logo(self) -> str:
        return self.core.competition_logo
    
    @competition_logo.setter
    def competition_logo(self, value: str):
        self.core.competition_logo = value
    
    # --- Facts プロパティ ---
    @property
    def home_lineup(self) -> List[str]:
        return self.facts.home_lineup
    
    @home_lineup.setter
    def home_lineup(self, value: List[str]):
        self.facts.home_lineup = value
    
    @property
    def away_lineup(self) -> List[str]:
        return self.facts.away_lineup
    
    @away_lineup.setter
    def away_lineup(self, value: List[str]):
        self.facts.away_lineup = value
    
    @property
    def home_bench(self) -> List[str]:
        return self.facts.home_bench
    
    @home_bench.setter
    def home_bench(self, value: List[str]):
        self.facts.home_bench = value
    
    @property
    def away_bench(self) -> List[str]:
        return self.facts.away_bench
    
    @away_bench.setter
    def away_bench(self, value: List[str]):
        self.facts.away_bench = value
    
    @property
    def home_formation(self) -> str:
        return self.facts.home_formation
    
    @home_formation.setter
    def home_formation(self, value: str):
        self.facts.home_formation = value
    
    @property
    def away_formation(self) -> str:
        return self.facts.away_formation
    
    @away_formation.setter
    def away_formation(self, value: str):
        self.facts.away_formation = value
    
    
    @property
    def home_recent_form_details(self) -> List[Dict]:
        return self.facts.home_recent_form_details
    
    @home_recent_form_details.setter
    def home_recent_form_details(self, value: List[Dict]):
        self.facts.home_recent_form_details = value
    
    @property
    def away_recent_form_details(self) -> List[Dict]:
        return self.facts.away_recent_form_details
    
    @away_recent_form_details.setter
    def away_recent_form_details(self, value: List[Dict]):
        self.facts.away_recent_form_details = value
    
    @property
    def player_nationalities(self) -> Dict[str, str]:
        return self.facts.player_nationalities
    
    @player_nationalities.setter
    def player_nationalities(self, value: Dict[str, str]):
        self.facts.player_nationalities = value
    
    @property
    def player_numbers(self) -> Dict[str, int]:
        return self.facts.player_numbers
    
    @player_numbers.setter
    def player_numbers(self, value: Dict[str, int]):
        self.facts.player_numbers = value
    
    @property
    def player_photos(self) -> Dict[str, str]:
        return self.facts.player_photos
    
    @player_photos.setter
    def player_photos(self, value: Dict[str, str]):
        self.facts.player_photos = value
    
    @property
    def player_birthdates(self) -> Dict[str, str]:
        return self.facts.player_birthdates
    
    @player_birthdates.setter
    def player_birthdates(self, value: Dict[str, str]):
        self.facts.player_birthdates = value
    
    @property
    def player_positions(self) -> Dict[str, str]:
        return self.facts.player_positions
    
    @player_positions.setter
    def player_positions(self, value: Dict[str, str]):
        self.facts.player_positions = value
    
    @property
    def player_instagram(self) -> Dict[str, str]:
        return self.facts.player_instagram
    
    @player_instagram.setter
    def player_instagram(self, value: Dict[str, str]):
        self.facts.player_instagram = value
    
    @property
    def injuries_list(self) -> List[Dict]:
        return self.facts.injuries_list
    
    @injuries_list.setter
    def injuries_list(self, value: List[Dict]):
        self.facts.injuries_list = value
    
    @property
    def injuries_info(self) -> str:
        return self.facts.injuries_info
    
    @injuries_info.setter
    def injuries_info(self, value: str):
        self.facts.injuries_info = value
    
    @property
    def h2h_summary(self) -> str:
        return self.facts.h2h_summary
    
    @h2h_summary.setter
    def h2h_summary(self, value: str):
        self.facts.h2h_summary = value
    
    @property
    def h2h_details(self) -> List[Dict]:
        return self.facts.h2h_details
    
    @h2h_details.setter
    def h2h_details(self, value: List[Dict]):
        self.facts.h2h_details = value
    
    @property
    def same_country_matchups(self) -> List[Dict]:
        return self.facts.same_country_matchups
    
    @same_country_matchups.setter
    def same_country_matchups(self, value: List[Dict]):
        self.facts.same_country_matchups = value
    
    @property
    def same_country_text(self) -> str:
        return self.facts.same_country_text
    
    @same_country_text.setter
    def same_country_text(self, value: str):
        self.facts.same_country_text = value
    
    @property
    def former_club_trivia(self) -> str:
        return self.facts.former_club_trivia
    
    @former_club_trivia.setter
    def former_club_trivia(self, value: str):
        self.facts.former_club_trivia = value
    
    @property
    def home_manager(self) -> str:
        return self.facts.home_manager
    
    @home_manager.setter
    def home_manager(self, value: str):
        self.facts.home_manager = value
    
    @property
    def away_manager(self) -> str:
        return self.facts.away_manager
    
    @away_manager.setter
    def away_manager(self, value: str):
        self.facts.away_manager = value
    
    @property
    def home_manager_photo(self) -> str:
        return self.facts.home_manager_photo
    
    @home_manager_photo.setter
    def home_manager_photo(self, value: str):
        self.facts.home_manager_photo = value
    
    @property
    def away_manager_photo(self) -> str:
        return self.facts.away_manager_photo
    
    @away_manager_photo.setter
    def away_manager_photo(self, value: str):
        self.facts.away_manager_photo = value
    
    # --- Preview プロパティ ---
    @property
    def news_summary(self) -> str:
        return self.preview.news_summary
    
    @news_summary.setter
    def news_summary(self, value: str):
        self.preview.news_summary = value
    
    @property
    def tactical_preview(self) -> str:
        return self.preview.tactical_preview
    
    @tactical_preview.setter
    def tactical_preview(self, value: str):
        self.preview.tactical_preview = value
    
    @property
    def preview_url(self) -> str:
        return self.preview.preview_url
    
    @preview_url.setter
    def preview_url(self, value: str):
        self.preview.preview_url = value
    
    @property
    def home_interview(self) -> str:
        return self.preview.home_interview
    
    @home_interview.setter
    def home_interview(self, value: str):
        self.preview.home_interview = value
    
    @property
    def away_interview(self) -> str:
        return self.preview.away_interview
    
    @away_interview.setter
    def away_interview(self, value: str):
        self.preview.away_interview = value
    
    # =========================================================================
    # ユーティリティメソッド
    # =========================================================================
    
    @staticmethod
    def _normalize_team_name(team_name: str) -> str:
        """チーム名をファイル名用に正規化"""
        normalized = team_name.replace(" ", "")
        normalized = re.sub(r'[^a-zA-Z0-9\-]', '', normalized)
        return normalized
    
    def get_report_filename(self, generation_datetime: str) -> str:
        """レポートファイル名を生成"""
        home_normalized = self._normalize_team_name(self.home_team)
        away_normalized = self._normalize_team_name(self.away_team)
        
        match_date = self.match_date_local
        if not match_date and self.kickoff_local:
            match_date = self.kickoff_local.split()[0] if self.kickoff_local else ""
        
        filename = f"{match_date}_{home_normalized}_vs_{away_normalized}_{generation_datetime}"
        return filename


# =============================================================================
# 既存クラス（後方互換性のため維持）
# =============================================================================

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
    h2h_details: list = None  # [{"date": str, "competition": str, "home": str, "away": str, "score": str, "winner": str}, ...]
    
    # 監督情報
    home_manager: str = ""
    away_manager: str = ""
    home_manager_photo: str = ""
    away_manager_photo: str = ""
    
    # チームロゴ
    home_logo: str = ""
    away_logo: str = ""
    
    # 大会ロゴ
    competition_logo: str = ""
    
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
        if self.h2h_details is None: self.h2h_details = []
    
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
