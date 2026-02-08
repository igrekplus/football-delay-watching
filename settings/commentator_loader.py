"""
U-NEXT解説者情報の読み込み・管理モジュール
"""

import csv
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "commentators")


@lru_cache(maxsize=1)
def load_all_commentators() -> dict[str, dict[str, str]]:
    """
    全リーグのCSVを読み込み、fixture_id をキーとしたマッピングを返す
    """
    all_data = {}

    if not os.path.exists(DATA_DIR):
        logger.warning(f"Commentators directory not found: {DATA_DIR}")
        return all_data

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".csv"):
            csv_path = os.path.join(DATA_DIR, filename)
            try:
                with open(csv_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        fid = row.get("fixture_id", "").strip()
                        if fid:
                            all_data[fid] = {
                                "commentator": row.get("commentator", "").strip(),
                                "announcer": row.get("announcer", "").strip(),
                            }
                            count += 1
                    logger.debug(f"Loaded {count} commentators from {filename}")
            except Exception as e:
                logger.error(f"Error loading commentator CSV {csv_path}: {e}")

    logger.info(f"Total commentator mappings loaded: {len(all_data)}")
    return all_data


def get_commentator_info(fixture_id: str | int) -> dict[str, str] | None:
    """
    指定されたfixture_idの解説者情報を取得
    """
    data = load_all_commentators()
    return data.get(str(fixture_id))


def clear_cache():
    """キャッシュをクリア"""
    load_all_commentators.cache_clear()
