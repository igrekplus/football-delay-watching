"""
カレンダー情報（解説者・レポートリンク）の読み込み・管理モジュール
"""

import csv
import logging
import os
import tempfile
from functools import lru_cache

logger = logging.getLogger(__name__)

# データディレクトリを commentators から calendar へ変更
DATA_DIR = os.path.join(os.path.dirname(__file__), "calendar")


@lru_cache(maxsize=1)
def load_all_calendar_data() -> dict[str, dict[str, str]]:
    """
    全リーグのCSVを読み込み、fixture_id をキーとしたマッピングを返す
    """
    all_data = {}

    if not os.path.exists(DATA_DIR):
        logger.warning(f"Calendar data directory not found: {DATA_DIR}")
        return all_data

    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".csv"):
            csv_path = os.path.join(DATA_DIR, filename)
            try:
                with open(csv_path, encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        fid = row.get("fixture_id", "").strip()
                        if fid:
                            all_data[fid] = {
                                "commentator": row.get("commentator", "").strip(),
                                "announcer": row.get("announcer", "").strip(),
                                "report_link": row.get("report_link", "").strip(),
                                "_source_file": csv_path,  # 更新時に使用するために元のファイルパスを保持
                            }
                            count += 1
                    logger.debug(f"Loaded {count} calendar entries from {filename}")
            except Exception as e:
                logger.error(f"Error loading calendar CSV {csv_path}: {e}")

    logger.info(f"Total calendar mappings loaded: {len(all_data)}")
    return all_data


def get_calendar_info(fixture_id: str | int) -> dict[str, str] | None:
    """
    指定されたfixture_idのカレンダー情報を取得
    """
    data = load_all_calendar_data()
    return data.get(str(fixture_id))


def update_report_link(
    fixture_id: str | int,
    report_link: str,
    league_name: str = None,
    match_data: dict = None,
) -> bool:
    """
    指定されたfixture_idのレポートリンクをCSVに書き込む。
    存在しない場合は新規行として追加する（league_nameが指定されている場合）。
    """
    # 表示名 → 内部名のマッピングを config.LEAGUE_INFO から動的に生成
    from config import config

    league_name_map = {}
    if hasattr(config, "LEAGUE_INFO"):
        for league in config.LEAGUE_INFO:
            display_name = league.get("display_name")
            internal_name = league.get("name")
            if display_name and internal_name and display_name != internal_name:
                league_name_map[display_name] = internal_name

    if league_name in league_name_map:
        league_name = league_name_map[league_name]

    fixture_id = str(fixture_id)
    data = load_all_calendar_data()
    info = data.get(fixture_id)

    if info:
        # 既存エントリの更新
        source_file = info.get("_source_file")
        if not source_file or not os.path.exists(source_file):
            logger.error(f"Source file for fixture {fixture_id} not found.")
            return False

        try:
            updated = False
            rows = []
            fieldnames = []

            with open(source_file, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row.get("fixture_id") == fixture_id:
                        row["report_link"] = report_link
                        updated = True
                    rows.append(row)

            if not updated:
                logger.warning(
                    f"Fixture ID {fixture_id} not found in {source_file} during update."
                )
                return False

            fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(source_file), text=True
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            os.replace(temp_path, source_file)
            clear_cache()
            logger.info(
                f"Updated report link for fixture {fixture_id} in {source_file}"
            )
            return True
        except Exception as e:
            logger.error(f"Error updating report link for fixture {fixture_id}: {e}")
            return False
    else:
        # 新規エントリの追加
        if not league_name:
            logger.warning(
                f"Fixture ID {fixture_id} not found and no league_name provided. Cannot append."
            )
            return False

        # リーグ名からファイル名を特定 (EPL -> epl.csv)
        csv_filename = f"{league_name.lower()}.csv"
        csv_path = os.path.join(DATA_DIR, csv_filename)

        if not os.path.exists(csv_path):
            logger.warning(f"CSV path {csv_path} does not exist. Creating new file.")
            # ヘッダーのみ作成
            header = [
                "fixture_id",
                "date_jst",
                "home_team",
                "away_team",
                "commentator",
                "announcer",
                "report_link",
            ]
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()

        try:
            # フィールド名の取得
            with open(csv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames

            # 新規行の作成
            new_row = {field: "" for field in fieldnames}
            new_row["fixture_id"] = fixture_id
            new_row["report_link"] = report_link
            if match_data:
                new_row["date_jst"] = match_data.get("date_jst", "")
                new_row["home_team"] = match_data.get("home_team", "")
                new_row["away_team"] = match_data.get("away_team", "")

            # 追記
            with open(csv_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(new_row)

            clear_cache()
            logger.info(f"Appended new fixture {fixture_id} to {csv_path}")
            return True
        except Exception as e:
            logger.error(f"Error appending fixture {fixture_id} to {csv_path}: {e}")
            return False


def clear_cache():
    """キャッシュをクリア"""
    load_all_calendar_data.cache_clear()


# 互換性のためのエイリアス
def get_commentator_info(fixture_id: str | int) -> dict[str, str] | None:
    return get_calendar_info(fixture_id)
