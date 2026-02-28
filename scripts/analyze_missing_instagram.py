from __future__ import annotations

import argparse
import csv
from pathlib import Path

DEFAULT_TEAM_ID = 50
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze missing Instagram URLs in a squad CSV"
    )
    parser.add_argument(
        "--team-id",
        type=int,
        default=DEFAULT_TEAM_ID,
        help="API-Football team ID used to resolve data/player_instagram_<team_id>.csv",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Explicit CSV path to analyze. Overrides --team-id when provided.",
    )
    return parser.parse_args()


def resolve_csv_path(team_id: int, csv_override: str | None) -> Path:
    if csv_override:
        csv_path = Path(csv_override)
    else:
        csv_path = Path("data") / f"player_instagram_{team_id}.csv"

    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path

    return csv_path


def main():
    args = parse_args()
    csv_path = resolve_csv_path(args.team_id, args.csv)
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    print(f"Analyzing {csv_path}...\n")

    missing_count = 0
    total_count = 0

    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            print(f"{'ID':<10} {'Name':<25} {'Position':<15} {'Number':<8}")
            print("-" * 60)

            for row in reader:
                total_count += 1
                url = row.get("instagram_url", "").strip()
                if not url:
                    missing_count += 1
                    print(
                        f"{row.get('player_id', ''):<10} {row.get('name', ''):<25} {row.get('position', ''):<15} {row.get('number', ''):<8}"
                    )

        print("\n" + "=" * 30)
        print(f"Total Players: {total_count}")
        print(f"Missing URLs : {missing_count}")
        print("=" * 30)

        if missing_count > 0:
            print("\nTip: Re-run with --team-id or --csv to target another squad file.")

    except Exception as e:
        print(f"Error reading CSV: {e}")


if __name__ == "__main__":
    main()
