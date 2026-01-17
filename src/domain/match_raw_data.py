from dataclasses import dataclass
from typing import Any


@dataclass
class MatchRawData:
    """APIから取得した生の試合データを保持するクラス（責務分割用の中間データ）"""

    lineups: dict[str, Any]
    injuries: dict[str, Any]
    home_form: dict[str, Any]
    away_form: dict[str, Any]
    h2h: dict[str, Any]
    home_team_id: int
    away_team_id: int
    fixture_details: dict[str, Any] | None = None
