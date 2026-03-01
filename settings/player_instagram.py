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
import io
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

# CSVファイルのパス（プロジェクトルートからの相対パス）
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PLAYER_DATA_GCS_PREFIX = os.getenv("PLAYER_DATA_GCS_PREFIX", "master/player")
USE_GCS_PLAYER_DATA = os.getenv("PLAYER_DATA_USE_GCS", "True").lower() == "true"

# チームID -> CSVファイル名のマッピング
TEAM_CSV_FILES = {
    33: "player_33.csv",  # Manchester United
    39: "player_39.csv",  # Wolves
    40: "player_40.csv",  # Liverpool
    42: "player_42.csv",  # Arsenal
    47: "player_47.csv",  # Tottenham
    49: "player_49.csv",  # Chelsea
    50: "player_50.csv",  # Manchester City
    66: "player_66.csv",  # Aston Villa
    # 将来的に他のチームを追加
}

_gcs_bucket = None
_gcs_client = None


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


def get_gcs_player_csv_path(csv_filename: str) -> str:
    """選手CSVのGCSパスを返す。"""
    return f"{PLAYER_DATA_GCS_PREFIX}/{csv_filename}"


def _get_gcs_bucket():
    """GCSバケットを遅延初期化して返す。"""
    global _gcs_bucket, _gcs_client

    from settings.cache_config import GCS_BUCKET_NAME

    if _gcs_bucket is not None:
        return _gcs_bucket

    from google.cloud import storage

    _gcs_client = storage.Client()
    _gcs_bucket = _gcs_client.bucket(GCS_BUCKET_NAME)
    return _gcs_bucket


def _rows_to_url_maps(
    rows: list[dict[str, str]], source_label: str
) -> tuple[dict[int, str], dict[str, str]]:
    """
    CSV行データから player_id / 選手名ごとのInstagram URLを返す。

    Returns:
        tuple[dict[int, str], dict[str, str]]:
            ({player_id: Instagram URL}, {選手名: Instagram URL})
    """
    urls_by_id: dict[int, str] = {}
    urls_by_name: dict[str, str] = {}

    try:
        for row in rows:
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
        logger.error(f"Error parsing Instagram CSV {source_label}: {e}")

    return urls_by_id, urls_by_name


def _load_local_csv(csv_path: str) -> tuple[dict[int, str], dict[str, str]]:
    """
    ローカルCSVファイルを読み込んで player_id / 選手名ごとのInstagram URLを返す
    """
    if not os.path.exists(csv_path):
        logger.warning(f"Instagram CSV not found: {csv_path}")
        return {}, {}

    try:
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return _rows_to_url_maps(list(reader), csv_path)
    except Exception as e:
        logger.error(f"Error loading Instagram CSV {csv_path}: {e}")
        return {}, {}


def _load_gcs_csv(csv_filename: str) -> tuple[dict[int, str], dict[str, str]] | None:
    """
    GCS上のCSVファイルを読み込んで player_id / 選手名ごとのInstagram URLを返す。

    Returns:
        tuple[dict[int, str], dict[str, str]] | None:
            GCSから読み込めた場合はマッピング、未配置または読込失敗時は None
    """
    try:
        bucket = _get_gcs_bucket()
        blob = bucket.blob(get_gcs_player_csv_path(csv_filename))
        if not blob.exists():
            logger.warning(f"Instagram CSV not found in GCS: {blob.name}")
            return None

        content = blob.download_as_text()
        if not content.strip():
            return {}, {}

        reader = csv.DictReader(io.StringIO(content))
        return _rows_to_url_maps(list(reader), blob.name)
    except Exception as e:
        logger.warning(f"Failed to load Instagram CSV from GCS ({csv_filename}): {e}")
        return None


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
        team_urls = _load_gcs_csv(csv_filename) if USE_GCS_PLAYER_DATA else None
        if team_urls is None:
            team_urls_by_id, team_urls_by_name = _load_local_csv(csv_path)
            if USE_GCS_PLAYER_DATA:
                logger.info(f"Using local fallback for Instagram CSV: {csv_filename}")
        else:
            team_urls_by_id, team_urls_by_name = team_urls
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
