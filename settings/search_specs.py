"""
検索仕様定義

YouTube検索・Google検索のクエリテンプレート、時間ウィンドウ、フィルタルールを集約。
チューニング時はこのファイルのみ変更すれば良い設計。

Issue #72: 検索仕様のデータ駆動化
"""

from datetime import datetime, timedelta
from typing import Any

# =============================================================================
# YouTube検索スペック
#
# 各カテゴリの検索仕様を定義。YouTubeServiceはこのスペックを参照して検索を実行する。
# =============================================================================

YOUTUBE_SEARCH_SPECS: dict[str, dict[str, Any]] = {
    "press_conference": {
        "label": "記者会見",
        "query_template": "{team_name} {manager_name} press conference",
        "query_template_no_manager": "{team_name} press conference",
        "window": {
            "hours_before": 48,  # キックオフの何時間前から
            "offset_hours": 0,  # キックオフの何時間前まで（0=キックオフまで）
        },
        "exclude_filters": [
            "match_highlights",
            "highlights",
            "full_match",
            "live_stream",
            "reaction",
        ],
        # playlist方式: チーム公式チャンネルのみ
        "allowed_channel_categories": ["team"],
        "title_keywords_type": "press_conference",  # "press conference" or "記者会見"
        "max_results": 50,
        "max_display": 2,
    },
    "historic": {
        "label": "過去の対戦",
        "query_template": "{home_team} vs {away_team} highlights",
        "window": {
            "days_before": 365,  # キックオフの何日前から（1年に短縮）
            "offset_hours": 24,  # キックオフの24時間前まで（ネタバレ防止）
        },
        "exclude_filters": ["live_stream", "press_conference", "reaction"],
        # playlist方式: UNEXT・チーム公式・リーグ・放送局
        "allowed_channel_categories": ["team", "league", "broadcaster"],
        "title_keywords_type": "both_teams",  # ホーム/アウェイ両チーム名
        "max_results": 50,
        "max_display": 3,
    },
    "tactical": {
        "label": "戦術分析",
        "query_template": "{team_name} 戦術 分析",
        "window": {
            "days_before": 180,  # 6ヶ月
            "offset_hours": 0,
        },
        "exclude_filters": [
            "match_highlights",
            "highlights",
            "full_match",
            "live_stream",
            "press_conference",
            "reaction",
        ],
        # playlist方式: 戦術専門チャンネルのみ（スポルティーバ含むtacticsカテゴリ）
        "allowed_channel_categories": ["tactics"],
        "title_keywords_type": "team_name",  # チーム名
        "max_results": 50,
        "max_display": 2,
    },
    "player_highlight": {
        "label": "選手紹介",
        "query_template": "{player_name} {team_name} プレー",
        "query_template_no_team": "{player_name} プレー",
        "window": {
            "days_before": 180,  # 6ヶ月
            "offset_hours": 0,
        },
        "exclude_filters": [
            "match_highlights",
            "highlights",
            "full_match",
            "live_stream",
            "press_conference",
            "reaction",
        ],
        # playlist方式: UNEXT・チーム公式・リーグ
        "allowed_channel_categories": ["team", "league", "broadcaster"],
        "title_keywords_type": "player_name",  # 選手名
        "max_results": 50,
        "max_display": 2,
    },
}


# =============================================================================
# ヘルパー関数
# =============================================================================


def build_youtube_query(category: str, **kwargs) -> str:
    """
    YouTubeスペックからクエリを生成

    Args:
        category: 検索カテゴリ（press_conference, historic等）
        **kwargs: テンプレート変数（team_name, manager_name等）

    Returns:
        検索クエリ文字列
    """
    spec = YOUTUBE_SEARCH_SPECS.get(category)
    if not spec:
        raise ValueError(f"Unknown YouTube search category: {category}")

    # manager_name がない場合は代替テンプレートを使用
    if category == "press_conference" and not kwargs.get("manager_name"):
        template = spec["query_template_no_manager"]
    elif category == "player_highlight" and not kwargs.get("team_name"):
        template = spec["query_template_no_team"]
    else:
        template = spec["query_template"]

    return template.format(**kwargs)


def get_youtube_time_window(
    category: str, kickoff_time: datetime
) -> tuple[datetime, datetime]:
    """
    YouTubeスペックから時間ウィンドウを計算

    Args:
        category: 検索カテゴリ
        kickoff_time: キックオフ時刻（UTC）

    Returns:
        (published_after, published_before)
    """
    spec = YOUTUBE_SEARCH_SPECS.get(category)
    if not spec:
        raise ValueError(f"Unknown YouTube search category: {category}")

    window = spec["window"]

    # 開始時刻の計算
    if "days_before" in window:
        published_after = kickoff_time - timedelta(days=window["days_before"])
    else:
        published_after = kickoff_time - timedelta(hours=window["hours_before"])

    # 終了時刻の計算
    offset_hours = window.get("offset_hours", 0)
    published_before = kickoff_time - timedelta(hours=offset_hours)

    return published_after, published_before


def get_youtube_allowed_channel_categories(category: str) -> list[str]:
    """カテゴリの許可チャンネルカテゴリリストを取得"""
    spec = YOUTUBE_SEARCH_SPECS.get(category)
    if not spec:
        raise ValueError(f"Unknown YouTube search category: {category}")
    return spec.get("allowed_channel_categories", [])


def get_youtube_max_display(category: str) -> int:
    """カテゴリの最大表示件数を取得"""
    spec = YOUTUBE_SEARCH_SPECS.get(category)
    if not spec:
        return 3
    return spec.get("max_display", 3)


def get_youtube_exclude_filters(category: str) -> list[str]:
    """
    YouTubeスペックから除外フィルタリストを取得

    Args:
        category: 検索カテゴリ

    Returns:
        除外フィルタ名のリスト
    """
    spec = YOUTUBE_SEARCH_SPECS.get(category)
    if not spec:
        raise ValueError(f"Unknown YouTube search category: {category}")

    return spec.get("exclude_filters", [])
