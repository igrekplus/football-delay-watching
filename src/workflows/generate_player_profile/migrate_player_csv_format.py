import argparse
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ensure player CSV files use the latest profile schema"
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing player_<team_id>.csv files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show files that would be updated without writing changes",
    )
    return parser.parse_args()


def resolve_data_dir(data_dir: str) -> Path:
    path = Path(data_dir)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def migrate_csv(csv_path: Path, dry_run: bool = False) -> bool:
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    required_fields = ["profile_format", "profile_detail"]
    missing_fields = [field for field in required_fields if field not in fieldnames]
    if not missing_fields:
        return False

    fieldnames.extend(missing_fields)
    for row in rows:
        for field in missing_fields:
            row[field] = row.get(field, "")

    print(f"MIGRATE {csv_path.name}: add {', '.join(missing_fields)}")
    if dry_run:
        return True

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return True


def main() -> int:
    args = parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    updated_count = 0

    for csv_path in sorted(data_dir.glob("player_*.csv")):
        if migrate_csv(csv_path, dry_run=args.dry_run):
            updated_count += 1

    print(f"Updated {updated_count} CSV files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
