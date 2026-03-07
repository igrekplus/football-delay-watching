"""
カレンダー情報（解説者・レポートリンク）の読み込み・管理モジュール
"""

import csv
import io
import logging
import os
import tempfile
from functools import lru_cache

logger = logging.getLogger(__name__)

# データディレクトリを commentators から calendar へ変更
DATA_DIR = os.path.join(os.path.dirname(__file__), "calendar")
GCS_CALENDAR_PREFIX = os.getenv("CALENDAR_STATUS_GCS_PREFIX", "schedule/calendar")
USE_GCS_CALENDAR_STATUS = os.getenv("CALENDAR_STATUS_USE_GCS", "True").lower() == "true"
CSV_COLUMNS = [
    "fixture_id",
    "date_jst",
    "home_team",
    "away_team",
    "commentator",
    "announcer",
    "report_link",
]

_gcs_bucket = None
_gcs_client = None
_gcs_versioning_checked = False


def _list_calendar_csv_files() -> list[str]:
    if not os.path.exists(DATA_DIR):
        return []
    return sorted(
        filename for filename in os.listdir(DATA_DIR) if filename.endswith(".csv")
    )


def _gcs_csv_path(csv_filename: str) -> str:
    return f"{GCS_CALENDAR_PREFIX}/{csv_filename}"


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


def _ensure_gcs_bucket_versioning(bucket) -> None:
    """GCSバケットのバージョニングを有効化（初回のみ確認）。"""
    global _gcs_versioning_checked

    if _gcs_versioning_checked:
        return

    try:
        bucket.reload()
        if bucket.versioning_enabled:
            logger.info("GCS bucket versioning is already enabled.")
        else:
            bucket.versioning_enabled = True
            bucket.patch()
            logger.info("Enabled GCS bucket versioning for calendar status.")
        _gcs_versioning_checked = True
    except Exception as e:
        logger.warning(f"Failed to ensure GCS bucket versioning: {e}")


def _load_local_csv_file(csv_path: str, csv_filename: str) -> dict[str, dict[str, str]]:
    data = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fid = row.get("fixture_id", "").strip()
            if not fid:
                continue
            data[fid] = {
                "commentator": row.get("commentator", "").strip(),
                "announcer": row.get("announcer", "").strip(),
                "report_link": row.get("report_link", "").strip(),
                "_source_file": csv_path,
                "_csv_filename": csv_filename,
            }
    return data


def _load_gcs_csv_rows(csv_filename: str) -> tuple[list[dict[str, str]], list[str]]:
    """GCS上のCSVを読み込み、行データとfieldnamesを返す。"""
    bucket = _get_gcs_bucket()
    blob = bucket.blob(_gcs_csv_path(csv_filename))

    if not blob.exists():
        return [], []

    content = blob.download_as_text()
    if not content.strip():
        return [], CSV_COLUMNS.copy()

    reader = csv.DictReader(io.StringIO(content))
    return list(reader), (reader.fieldnames or CSV_COLUMNS.copy())


def _read_local_csv_rows(csv_path: str) -> tuple[list[dict[str, str]], list[str]]:
    if not os.path.exists(csv_path):
        return [], CSV_COLUMNS.copy()

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, (reader.fieldnames or CSV_COLUMNS.copy())


def _merge_gcs_calendar_data(
    all_data: dict[str, dict[str, str]], local_filenames: list[str]
):
    """ローカルCSVをベースに、GCS上の最新report_link等を上書きする。"""
    if not USE_GCS_CALENDAR_STATUS:
        return

    try:
        for csv_filename in local_filenames:
            rows, _fieldnames = _load_gcs_csv_rows(csv_filename)
            gcs_path = _gcs_csv_path(csv_filename)

            for row in rows:
                fixture_id = row.get("fixture_id", "").strip()
                if not fixture_id:
                    continue

                existing = all_data.get(
                    fixture_id,
                    {
                        "commentator": "",
                        "announcer": "",
                        "report_link": "",
                    },
                )

                commentator = row.get("commentator", "").strip()
                announcer = row.get("announcer", "").strip()
                if commentator:
                    existing["commentator"] = commentator
                if announcer:
                    existing["announcer"] = announcer
                existing["report_link"] = row.get("report_link", "").strip()
                existing["_csv_filename"] = csv_filename
                existing["_gcs_source_file"] = gcs_path

                if "_source_file" not in existing:
                    local_path = os.path.join(DATA_DIR, csv_filename)
                    existing["_source_file"] = local_path

                all_data[fixture_id] = existing
    except Exception as e:
        logger.warning(f"Skipping GCS calendar overlay due to error: {e}")


def _resolve_csv_filename(
    fixture_id: str, info: dict[str, str] | None, league_name: str | None
) -> str | None:
    if info and info.get("_csv_filename"):
        return info["_csv_filename"]

    if info and info.get("_source_file"):
        return os.path.basename(info["_source_file"])

    if league_name:
        return f"{league_name.lower()}.csv"

    logger.warning(
        f"Fixture ID {fixture_id} not found and no league_name provided. Cannot append."
    )
    return None


def _candidate_csv_filenames(local_filenames: list[str]) -> list[str]:
    filenames = set(local_filenames)

    try:
        from config import config

        for league in getattr(config, "LEAGUE_INFO", []):
            league_name = league.get("name")
            if league_name:
                filenames.add(f"{league_name.lower()}.csv")
    except Exception:
        pass

    return sorted(filenames)


def _build_new_row(
    fieldnames: list[str], fixture_id: str, report_link: str, match_data: dict | None
) -> dict[str, str]:
    new_row = {field: "" for field in fieldnames}
    new_row["fixture_id"] = fixture_id
    new_row["report_link"] = report_link
    if match_data:
        new_row["date_jst"] = match_data.get("date_jst", "")
        new_row["home_team"] = match_data.get("home_team", "")
        new_row["away_team"] = match_data.get("away_team", "")
    return new_row


def _write_gcs_csv_rows(
    csv_filename: str, rows: list[dict[str, str]], fieldnames: list[str]
) -> bool:
    try:
        bucket = _get_gcs_bucket()
        _ensure_gcs_bucket_versioning(bucket)

        normalized_fields = fieldnames.copy()
        for required in CSV_COLUMNS:
            if required not in normalized_fields:
                normalized_fields.append(required)

        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=normalized_fields, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)

        blob = bucket.blob(_gcs_csv_path(csv_filename))
        blob.upload_from_string(output.getvalue(), content_type="text/csv")
        return True
    except Exception as e:
        logger.warning(f"Failed to write calendar CSV to GCS ({csv_filename}): {e}")
        return False


def _update_report_link_in_gcs(
    csv_filename: str, fixture_id: str, report_link: str, match_data: dict | None
) -> bool:
    try:
        rows, fieldnames = _load_gcs_csv_rows(csv_filename)
        if not rows:
            local_csv_path = os.path.join(DATA_DIR, csv_filename)
            rows, local_fieldnames = _read_local_csv_rows(local_csv_path)
            fieldnames = local_fieldnames

        if not fieldnames:
            fieldnames = CSV_COLUMNS.copy()

        updated = False
        for row in rows:
            if row.get("fixture_id", "").strip() == fixture_id:
                row["report_link"] = report_link
                if match_data:
                    row["date_jst"] = row.get("date_jst") or match_data.get(
                        "date_jst", ""
                    )
                    row["home_team"] = row.get("home_team") or match_data.get(
                        "home_team", ""
                    )
                    row["away_team"] = row.get("away_team") or match_data.get(
                        "away_team", ""
                    )
                updated = True
                break

        if not updated:
            rows.append(_build_new_row(fieldnames, fixture_id, report_link, match_data))

        if not _write_gcs_csv_rows(csv_filename, rows, fieldnames):
            return False

        logger.info(
            f"Updated report link for fixture {fixture_id} in GCS ({_gcs_csv_path(csv_filename)})"
        )
        clear_cache()
        return True
    except Exception as e:
        logger.warning(
            f"Failed to update report link in GCS for fixture {fixture_id}: {e}"
        )
        return False


def _update_report_link_in_local_csv(
    csv_filename: str, fixture_id: str, report_link: str, match_data: dict | None
) -> bool:
    csv_path = os.path.join(DATA_DIR, csv_filename)

    if not os.path.exists(csv_path):
        logger.warning(f"CSV path {csv_path} does not exist. Creating new file.")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()

    try:
        updated = False
        rows = []
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or CSV_COLUMNS.copy()
            for row in reader:
                if row.get("fixture_id", "").strip() == fixture_id:
                    row["report_link"] = report_link
                    if match_data:
                        row["date_jst"] = row.get("date_jst") or match_data.get(
                            "date_jst", ""
                        )
                        row["home_team"] = row.get("home_team") or match_data.get(
                            "home_team", ""
                        )
                        row["away_team"] = row.get("away_team") or match_data.get(
                            "away_team", ""
                        )
                    updated = True
                rows.append(row)

        if not updated:
            rows.append(_build_new_row(fieldnames, fixture_id, report_link, match_data))

        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(csv_path), text=True)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        os.replace(temp_path, csv_path)
        clear_cache()
        logger.info(
            f"Updated report link for fixture {fixture_id} in local CSV ({csv_path})"
        )
        return True
    except Exception as e:
        logger.error(f"Error updating report link for fixture {fixture_id}: {e}")
        return False


@lru_cache(maxsize=1)
def load_all_calendar_data() -> dict[str, dict[str, str]]:
    """
    全リーグのCSVを読み込み、fixture_id をキーとしたマッピングを返す
    """
    all_data = {}
    local_filenames = _list_calendar_csv_files()
    candidate_filenames = _candidate_csv_filenames(local_filenames)

    if not local_filenames:
        logger.warning(f"Calendar data directory not found: {DATA_DIR}")
    else:
        for filename in local_filenames:
            csv_path = os.path.join(DATA_DIR, filename)
            try:
                loaded = _load_local_csv_file(csv_path, filename)
                all_data.update(loaded)
                logger.debug(f"Loaded {len(loaded)} calendar entries from {filename}")
            except Exception as e:
                logger.error(f"Error loading calendar CSV {csv_path}: {e}")

    _merge_gcs_calendar_data(all_data, candidate_filenames)

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
    csv_filename = _resolve_csv_filename(fixture_id, info, league_name)
    if not csv_filename:
        return False

    if USE_GCS_CALENDAR_STATUS and _update_report_link_in_gcs(
        csv_filename, fixture_id, report_link, match_data
    ):
        return True

    if USE_GCS_CALENDAR_STATUS:
        logger.warning(
            f"Falling back to local CSV update for fixture {fixture_id} due to GCS failure."
        )

    return _update_report_link_in_local_csv(
        csv_filename, fixture_id, report_link, match_data
    )


def clear_cache():
    """キャッシュをクリア"""
    load_all_calendar_data.cache_clear()


# 互換性のためのエイリアス
def get_commentator_info(fixture_id: str | int) -> dict[str, str] | None:
    return get_calendar_info(fixture_id)
