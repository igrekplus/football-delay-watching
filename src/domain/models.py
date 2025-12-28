"""
ドメインモデル

試合データやその他のドメインオブジェクトを定義

Issue #69: 責務分離のためのサブ構造
- MatchCore: 試合の基本情報（MatchProcessorで生成）
- MatchFacts: API取得データ（FactsServiceで生成）
- MatchPreview: LLM生成データ（NewsServiceで生成）
- MatchMedia: YouTube・画像データ
- MatchAggregate: 統合コンテナ
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import re


# =============================================================================
# Issue #69: 新しいサブ構造クラス
# =============================================================================

@dataclass
class MatchCore:
    """試合の基本情報（MatchProcessorで生成）"""
    id: str
    home_team: str
    away_team: str
    competition: str  # EPL, CL, LaLiga, etc.
    kickoff_jst: str
    kickoff_local: str
    rank: str  # Absolute, S, A, or None
    selection_reason: str = ""
    is_target: bool = False
    match_date_local: str = ""  # 試合開催日（現地時間）YYYY-MM-DD
    # Issue #70: timezone-aware datetime (UTC)
    kickoff_at_utc: Optional[datetime] = None


@dataclass
class MatchFacts:
    """API取得データ（FactsServiceで生成）"""
    # Lineup & Formation
    home_lineup: List[str] = field(default_factory=list)
    away_lineup: List[str] = field(default_factory=list)
    home_bench: List[str] = field(default_factory=list)
    away_bench: List[str] = field(default_factory=list)
    home_formation: str = ""
    away_formation: str = ""
    
    # Match Info
    venue: str = ""
    referee: str = ""
    home_recent_form: str = ""
    away_recent_form: str = ""
    h2h_summary: str = ""
    
    # Manager Info
    home_manager: str = ""
    away_manager: str = ""
    home_manager_photo: str = ""
    away_manager_photo: str = ""
    
    # Team Logos
    home_logo: str = ""
    away_logo: str = ""
    
    # Player Details (name -> value mapping)
    player_nationalities: Dict[str, str] = field(default_factory=dict)
    player_numbers: Dict[str, int] = field(default_factory=dict)
    player_photos: Dict[str, str] = field(default_factory=dict)
    player_birthdates: Dict[str, str] = field(default_factory=dict)
    player_positions: Dict[str, str] = field(default_factory=dict)
    
    # Injuries and Suspensions
    injuries_list: List[Dict] = field(default_factory=list)
    injuries_info: str = "不明"


@dataclass
class MatchPreview:
    """LLM生成データ（NewsServiceで生成）"""
    news_summary: str = ""
    tactical_preview: str = ""
    preview_url: str = ""
    home_interview: str = ""
    away_interview: str = ""


@dataclass
class MatchMedia:
    """YouTube・画像データ"""
    videos: Dict[str, List[Dict]] = field(default_factory=dict)
    formation_image_paths: List[str] = field(default_factory=list)


@dataclass
class MatchAggregate:
    """
    統合コンテナ
    
    生成順序: Core -> Facts -> Preview -> Media
    - MatchProcessor: core を生成
    - FactsService: facts を生成（core を参照）
    - NewsService: preview を生成（core, facts を参照）
    - YouTubeService/ReportGenerator: media を生成
    """
    core: MatchCore
    facts: MatchFacts = field(default_factory=MatchFacts)
    preview: MatchPreview = field(default_factory=MatchPreview)
    media: MatchMedia = field(default_factory=MatchMedia)
    error_status: str = "Normal"  # Normal, E1, E2, E3
    
    # =========================================================================
    # 後方互換プロパティ（既存コードからのアクセスをサポート）
    # Phase 5 で削除予定
    # =========================================================================
    
    @property
    def id(self) -> str:
        return self.core.id
    
    @property
    def home_team(self) -> str:
        return self.core.home_team
    
    @property
    def away_team(self) -> str:
        return self.core.away_team
    
    @property
    def competition(self) -> str:
        return self.core.competition
    
    @property
    def kickoff_jst(self) -> str:
        return self.core.kickoff_jst
    
    @property
    def kickoff_local(self) -> str:
        return self.core.kickoff_local
    
    @property
    def rank(self) -> str:
        return self.core.rank
    
    @property
    def selection_reason(self) -> str:
        return self.core.selection_reason
    
    @property
    def is_target(self) -> bool:
        return self.core.is_target
    
    @property
    def match_date_local(self) -> str:
        return self.core.match_date_local
    
    # Issue #70: kickoff_at_utc プロパティを追加
    @property
    def kickoff_at_utc(self) -> Optional[datetime]:
        return self.core.kickoff_at_utc


# =============================================================================
# 既存クラス（後方互換性のため維持）
# =============================================================================

@dataclass
class MatchData:
    """
    試合データを保持するデータクラス
    
    Issue #69 により、責務分離のためのサブ構造クラスが導入された:
    - MatchCore: 試合の基本情報
    - MatchFacts: API取得データ
    - MatchPreview: LLM生成データ
    - MatchMedia: YouTube・画像データ
    - MatchAggregate: 統合コンテナ
    
    このクラスは後方互換性のため維持されているが、
    将来的には MatchAggregate への移行を推奨。
    
    変換メソッド:
    - to_facts() / set_facts(): MatchFacts との相互変換
    - to_preview() / set_preview(): MatchPreview との相互変換
    - to_core(): MatchCore への変換
    - to_aggregate(): MatchAggregate への変換
    """
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
    
    # Issue #70: timezone-aware datetime (UTC)
    kickoff_at_utc: Optional[datetime] = None
    
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
    
    # =========================================================================
    # Issue #69: MatchFacts/MatchPreview との相互変換メソッド
    # =========================================================================
    
    def to_facts(self) -> 'MatchFacts':
        """現在のフィールドから MatchFacts オブジェクトを生成"""
        return MatchFacts(
            home_lineup=self.home_lineup,
            away_lineup=self.away_lineup,
            home_bench=self.home_bench,
            away_bench=self.away_bench,
            home_formation=self.home_formation,
            away_formation=self.away_formation,
            venue=self.venue,
            referee=self.referee,
            home_recent_form=self.home_recent_form,
            away_recent_form=self.away_recent_form,
            h2h_summary=self.h2h_summary,
            home_manager=self.home_manager,
            away_manager=self.away_manager,
            home_manager_photo=self.home_manager_photo,
            away_manager_photo=self.away_manager_photo,
            home_logo=self.home_logo,
            away_logo=self.away_logo,
            player_nationalities=self.player_nationalities,
            player_numbers=self.player_numbers,
            player_photos=self.player_photos,
            player_birthdates=self.player_birthdates,
            player_positions=self.player_positions,
            injuries_list=self.injuries_list,
            injuries_info=self.injuries_info,
        )
    
    def set_facts(self, facts: 'MatchFacts') -> None:
        """MatchFacts オブジェクトから対応フィールドを設定"""
        self.home_lineup = facts.home_lineup
        self.away_lineup = facts.away_lineup
        self.home_bench = facts.home_bench
        self.away_bench = facts.away_bench
        self.home_formation = facts.home_formation
        self.away_formation = facts.away_formation
        self.venue = facts.venue
        self.referee = facts.referee
        self.home_recent_form = facts.home_recent_form
        self.away_recent_form = facts.away_recent_form
        self.h2h_summary = facts.h2h_summary
        self.home_manager = facts.home_manager
        self.away_manager = facts.away_manager
        self.home_manager_photo = facts.home_manager_photo
        self.away_manager_photo = facts.away_manager_photo
        self.home_logo = facts.home_logo
        self.away_logo = facts.away_logo
        self.player_nationalities = facts.player_nationalities
        self.player_numbers = facts.player_numbers
        self.player_photos = facts.player_photos
        self.player_birthdates = facts.player_birthdates
        self.player_positions = facts.player_positions
        self.injuries_list = facts.injuries_list
        self.injuries_info = facts.injuries_info
    
    def to_preview(self) -> 'MatchPreview':
        """現在のフィールドから MatchPreview オブジェクトを生成"""
        return MatchPreview(
            news_summary=self.news_summary,
            tactical_preview=self.tactical_preview,
            preview_url=self.preview_url,
            home_interview=self.home_interview,
            away_interview=self.away_interview,
        )
    
    def set_preview(self, preview: 'MatchPreview') -> None:
        """MatchPreview オブジェクトから対応フィールドを設定"""
        self.news_summary = preview.news_summary
        self.tactical_preview = preview.tactical_preview
        self.preview_url = preview.preview_url
        self.home_interview = preview.home_interview
        self.away_interview = preview.away_interview
    
    def to_core(self) -> 'MatchCore':
        """現在のフィールドから MatchCore オブジェクトを生成"""
        return MatchCore(
            id=self.id,
            home_team=self.home_team,
            away_team=self.away_team,
            competition=self.competition,
            kickoff_jst=self.kickoff_jst,
            kickoff_local=self.kickoff_local,
            rank=self.rank,
            selection_reason=self.selection_reason,
            is_target=self.is_target,
            match_date_local=self.match_date_local,
            kickoff_at_utc=self.kickoff_at_utc,
        )
    
    def to_aggregate(self) -> 'MatchAggregate':
        """現在のMatchDataから MatchAggregate を生成"""
        return MatchAggregate(
            core=self.to_core(),
            facts=self.to_facts(),
            preview=self.to_preview(),
            error_status=self.error_status,
        )

