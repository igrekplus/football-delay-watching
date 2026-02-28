"""
選手Instagram URL管理モジュール

CSVファイルから選手ID/名前とInstagram URLのマッピングを読み込む。
実行時の紐づけは player_id を優先し、モック用途では名前でも参照できる。

Usage:
    from settings.player_instagram import get_player_instagram_urls

    # 選手ID -> Instagram URL のマッピングを取得
    instagram_urls = get_player_instagram_urls()
    url = instagram_urls.get(1100)  # https://www.instagram.com/erling/
"""

from __future__ import annotations

import csv
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# CSVファイルのパス（プロジェクトルートからの相対パス）
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# チームID -> CSVファイル名のマッピング
TEAM_CSV_FILES = {
    33: "player_instagram_33.csv",  # Manchester United
    39: "player_instagram_39.csv",  # Wolves
    40: "player_instagram_40.csv",  # Liverpool
    42: "player_instagram_42.csv",  # Arsenal
    47: "player_instagram_47.csv",  # Tottenham
    49: "player_instagram_49.csv",  # Chelsea
    50: "player_instagram_50.csv",  # Manchester City
    66: "player_instagram_66.csv",  # Aston Villa
    # 将来的に他のチームを追加
}


def _parse_player_id(raw_player_id: str) -> int | None:
    """CSVの player_id を整数に正規化する。"""
    player_id = str(raw_player_id).strip()
    if not player_id:
        return None

    try:
        return int(player_id)
    except ValueError:
        logger.warning(f"Invalid player_id in Instagram CSV: {raw_player_id}")
        return None


def _load_csv(csv_path: str) -> tuple[dict[int, str], dict[str, str]]:
    """
    CSVファイルを読み込んで player_id / 選手名ごとのInstagram URLを返す

    Returns:
        tuple[dict[int, str], dict[str, str]]:
            ({player_id: Instagram URL}, {選手名: Instagram URL})
    """
    urls_by_id: dict[int, str] = {}
    urls_by_name: dict[str, str] = {}

    if not os.path.exists(csv_path):
        logger.warning(f"Instagram CSV not found: {csv_path}")
        return urls_by_id, urls_by_name

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name", "").strip()
                url = row.get("instagram_url", "").strip()
                if not url:
                    continue
                player_id = _parse_player_id(row.get("player_id", ""))
                if player_id is not None:
                    urls_by_id[player_id] = url
                if name:
                    urls_by_name[name] = url
    except Exception as e:
        logger.error(f"Error loading Instagram CSV {csv_path}: {e}")

    return urls_by_id, urls_by_name


@lru_cache(maxsize=1)
def _load_all_instagram_urls() -> tuple[dict[int, str], dict[str, str]]:
    """
    全てのCSVファイルから player_id / 選手名ごとのInstagram URLマッピングを取得

    Returns:
        tuple[dict[int, str], dict[str, str]]:
            ({player_id: Instagram URL}, {選手名: Instagram URL})
    """
    all_urls_by_id: dict[int, str] = {}
    all_urls_by_name: dict[str, str] = {}

    for _, csv_filename in TEAM_CSV_FILES.items():
        csv_path = os.path.join(DATA_DIR, csv_filename)
        team_urls_by_id, team_urls_by_name = _load_csv(csv_path)
        all_urls_by_id.update(team_urls_by_id)
        all_urls_by_name.update(team_urls_by_name)

        if team_urls_by_id:
            logger.debug(
                f"Loaded {len(team_urls_by_id)} Instagram URLs from {csv_filename}"
            )

    logger.info(f"Total Instagram URLs loaded: {len(all_urls_by_id)}")
    return all_urls_by_id, all_urls_by_name


def get_player_instagram_urls() -> dict[int, str]:
    """
    全てのCSVファイルから player_id -> Instagram URL のマッピングを取得

    Returns:
        dict[int, str]: {player_id: Instagram URL}
    """
    urls_by_id, _ = _load_all_instagram_urls()
    return urls_by_id


def get_player_instagram_urls_by_id() -> dict[int, str]:
    """`get_player_instagram_urls` の明示的な別名。"""
    return get_player_instagram_urls()


def get_player_instagram_urls_by_name() -> dict[str, str]:
    """
    全てのCSVファイルから 選手名 -> Instagram URL のマッピングを取得

    Returns:
        dict[str, str]: {選手名: Instagram URL}
    """
    _, urls_by_name = _load_all_instagram_urls()
    return urls_by_name


def get_instagram_url(player_id: int | str) -> str | None:
    """
    選手IDからInstagram URLを取得

    Args:
        player_id: 選手ID（API-Footballの player_id）

    Returns:
        Instagram URL or None
    """
    normalized_player_id = _parse_player_id(player_id)
    if normalized_player_id is None:
        return None

    urls = get_player_instagram_urls()
    return urls.get(normalized_player_id)


def clear_cache():
    """キャッシュをクリア（CSVを更新した後に呼び出す）"""
    _load_all_instagram_urls.cache_clear()


# デバッグ用: 直接実行時にCSVの内容を表示
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    urls = get_player_instagram_urls()
    print(f"\n📸 Instagram URLs ({len(urls)} players):")
    for player_id, url in sorted(urls.items()):
        print(f"  - {player_id}: {url}")
