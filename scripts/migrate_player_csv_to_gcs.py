from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload local player CSV files to the configured GCS bucket"
    )
    parser.add_argument(
        "--team-id",
        type=int,
        action="append",
        help="Specific API-Football team ID to upload. Can be specified multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned uploads without modifying GCS.",
    )
    return parser.parse_args()


def iter_target_files(team_ids: list[int] | None) -> list[tuple[int, str, Path]]:
    from settings.player_instagram import DATA_DIR, TEAM_CSV_FILES

    selected_ids = team_ids or sorted(TEAM_CSV_FILES)
    targets: list[tuple[int, str, Path]] = []
    for team_id in selected_ids:
        csv_filename = TEAM_CSV_FILES.get(team_id)
        if not csv_filename:
            raise ValueError(f"Unknown team_id: {team_id}")
        local_path = Path(DATA_DIR) / csv_filename
        targets.append((team_id, csv_filename, local_path))
    return targets


def upload_csvs(team_ids: list[int] | None, dry_run: bool = False) -> int:
    from google.cloud import storage

    from settings.cache_config import GCS_BUCKET_NAME
    from settings.player_instagram import get_gcs_player_csv_path

    bucket = storage.Client().bucket(GCS_BUCKET_NAME)
    uploaded = 0

    for team_id, csv_filename, local_path in iter_target_files(team_ids):
        if not local_path.exists():
            print(f"SKIP team={team_id} missing local file: {local_path}")
            continue

        blob_path = get_gcs_player_csv_path(csv_filename)
        print(
            f"UPLOAD team={team_id} {local_path} -> gs://{GCS_BUCKET_NAME}/{blob_path}"
        )
        if dry_run:
            continue

        bucket.blob(blob_path).upload_from_filename(
            str(local_path), content_type="text/csv"
        )
        uploaded += 1

    return uploaded


def main() -> int:
    args = parse_args()
    try:
        uploaded = upload_csvs(args.team_id, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}")
        return 1

    if args.dry_run:
        print("Dry run completed.")
    else:
        print(f"Uploaded {uploaded} CSV files to GCS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
