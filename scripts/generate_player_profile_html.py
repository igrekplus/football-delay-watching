import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate standalone player profile HTML from a team CSV row"
    )
    parser.add_argument(
        "--team-id",
        type=int,
        required=True,
        help="API-Football team ID that owns the source player CSV",
    )
    parser.add_argument(
        "--player-id",
        required=True,
        help="API-Football player ID to render",
    )
    parser.add_argument(
        "--output-path",
        help="Explicit output HTML path. Relative paths are resolved from the project root.",
    )
    parser.add_argument(
        "--output-dir",
        default="public/player-profiles",
        help="Directory for generated profile HTML when --output-path is omitted",
    )
    return parser.parse_args()


def resolve_project_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def resolve_csv_path(team_id: int) -> Path:
    from settings.player_instagram import DATA_DIR, TEAM_CSV_FILES

    csv_filename = TEAM_CSV_FILES.get(team_id)
    if not csv_filename:
        raise ValueError(f"Unknown team_id: {team_id}")

    data_dir = Path(DATA_DIR)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    return data_dir / csv_filename


def load_player_row(team_id: int, player_id: str) -> dict[str, str]:
    csv_path = resolve_csv_path(team_id)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("player_id") == str(player_id):
                return row

    raise ValueError(f"player_id={player_id} not found in {csv_path}")


def resolve_output_path(
    player_id: str,
    player_name: str,
    output_path: str | None,
    output_dir: str,
) -> Path:
    from src.utils.player_profile import build_player_profile_slug

    if output_path:
        return resolve_project_path(output_path)

    resolved_output_dir = resolve_project_path(output_dir)
    existing_files = sorted(resolved_output_dir.glob(f"{player_id}-*.html"))
    if len(existing_files) == 1:
        return existing_files[0]
    if len(existing_files) > 1:
        raise ValueError(
            f"Multiple existing standalone profile files found for player_id={player_id}: "
            + ", ".join(str(path) for path in existing_files)
        )

    slug = build_player_profile_slug(int(player_id), player_name)
    return resolved_output_dir / f"{slug}.html"


def render_profile_html(row: dict[str, str]) -> str:
    from src.template_engine import render_template
    from src.utils.player_profile import (
        parse_player_profile_sections,
        validate_player_profile_sections,
    )

    profile = {
        "format": row.get("profile_format", ""),
        "detail": row.get("profile_detail", ""),
    }
    sections = parse_player_profile_sections(profile)
    if not sections:
        raise ValueError(
            f"player_id={row.get('player_id')} has no renderable profile_detail"
        )
    validate_player_profile_sections(
        sections,
        player_id=row.get("player_id"),
        player_name=row.get("name"),
    )

    return render_template("partials/player_profile_standalone.html", sections=sections)


def generate_player_profile_html(
    team_id: int,
    player_id: str,
    output_path: str | None = None,
    output_dir: str = "public/player-profiles",
) -> Path:
    row = load_player_row(team_id, player_id)
    resolved_output_path = resolve_output_path(
        player_id=player_id,
        player_name=row["name"],
        output_path=output_path,
        output_dir=output_dir,
    )
    html = render_profile_html(row)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(html, encoding="utf-8")
    return resolved_output_path


def main() -> int:
    args = parse_args()
    try:
        output_path = generate_player_profile_html(
            team_id=args.team_id,
            player_id=str(args.player_id),
            output_path=args.output_path,
            output_dir=args.output_dir,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    print(f"Generated standalone profile HTML: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
