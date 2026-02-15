"""
選手Instagram URL管理モジュール

CSVファイルから選手ID/名前とInstagram URLのマッピングを読み込む。
手動でCSVを更新することで、選手のInstagramリンクを管理できる。

Usage:
    from settings.player_instagram import get_player_instagram_urls

    # 選手名 -> Instagram URL のマッピングを取得
    instagram_urls = get_player_instagram_urls()
    url = instagram_urls.get("E. Haaland")  # https://www.instagram.com/erling/
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
    50: "player_instagram_50.csv",  # Manchester City
    # 将来的に他のチームを追加
    # 42: "player_instagram_42.csv",  # Arsenal
    # 40: "player_instagram_40.csv",  # Liverpool
}


def _load_csv(csv_path: str) -> dict[str, str]:
    """
    CSVファイルを読み込んで選手名 -> Instagram URLのマッピングを返す

    Returns:
        Dict[str, str]: {選手名: Instagram URL}
    """
    result = {}

    if not os.path.exists(csv_path):
        logger.warning(f"Instagram CSV not found: {csv_path}")
        return result

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name", "").strip()
                url = row.get("instagram_url", "").strip()
                if name and url:
                    result[name] = url
    except Exception as e:
        logger.error(f"Error loading Instagram CSV {csv_path}: {e}")

    return result


@lru_cache(maxsize=1)
def get_player_instagram_urls() -> dict[str, str]:
    """
    全てのCSVファイルから選手名 -> Instagram URLのマッピングを取得

    Returns:
        Dict[str, str]: {選手名: Instagram URL}
    """
    all_urls = {}

    for team_id, csv_filename in TEAM_CSV_FILES.items():
        csv_path = os.path.join(DATA_DIR, csv_filename)
        team_urls = _load_csv(csv_path)
        all_urls.update(team_urls)

        if team_urls:
            logger.debug(f"Loaded {len(team_urls)} Instagram URLs from {csv_filename}")

    logger.info(f"Total Instagram URLs loaded: {len(all_urls)}")
    return all_urls


def get_instagram_url(player_name: str) -> str | None:
    """
    選手名からInstagram URLを取得

    Args:
        player_name: 選手名（API-Footballの表記に準拠）

    Returns:
        Instagram URL or None
    """
    urls = get_player_instagram_urls()
    return urls.get(player_name)


def clear_cache():
    """キャッシュをクリア（CSVを更新した後に呼び出す）"""
    get_player_instagram_urls.cache_clear()


# デバッグ用: 直接実行時にCSVの内容を表示
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    urls = get_player_instagram_urls()
    print(f"\n📸 Instagram URLs ({len(urls)} players):")
    for name, url in sorted(urls.items()):
        print(f"  - {name}: {url}")
