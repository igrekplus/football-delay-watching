from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class MatchRawData:
    """APIから取得した生の試合データを保持するクラス（責務分割用の中間データ）"""
    lineups: Dict[str, Any]
    injuries: Dict[str, Any]
    home_form: Dict[str, Any]
    away_form: Dict[str, Any]
    h2h: Dict[str, Any]
    home_team_id: int
    away_team_id: int
    fixture_details: Optional[Dict[str, Any]] = None
