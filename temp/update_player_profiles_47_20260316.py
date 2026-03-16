import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data/player_47.csv"

PROFILE_FILES = {
    "30776": PROJECT_ROOT
    / "temp/player_profiles_20260316_tottenham_cristian_romero.md",
    "152849": PROJECT_ROOT
    / "temp/player_profiles_20260316_tottenham_micky_van_de_ven.md",
    "47519": PROJECT_ROOT / "temp/player_profiles_20260316_tottenham_pedro_porro.md",
    "237129": PROJECT_ROOT
    / "temp/player_profiles_20260316_tottenham_pape_matar_sarr.md",
    "2413": PROJECT_ROOT / "temp/player_profiles_20260316_tottenham_richarlison.md",
}


def extract_profile_detail(markdown_path: Path) -> str:
    text = markdown_path.read_text(encoding="utf-8")
    start = text.index("```text") + len("```text")
    end = text.index("```", start)
    return text[start:end].strip()


def main() -> None:
    profiles = {
        player_id: extract_profile_detail(path)
        for player_id, path in PROFILE_FILES.items()
    }

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    updated = 0
    for row in rows:
        player_id = row["player_id"]
        if player_id not in profiles:
            continue
        row["profile_format"] = "labelled_lines_v1"
        row["profile_detail"] = profiles[player_id]
        updated += 1

    if updated != len(PROFILE_FILES):
        raise RuntimeError(
            f"Expected to update {len(PROFILE_FILES)} rows but updated {updated}"
        )

    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated} player profiles in {CSV_PATH}")


if __name__ == "__main__":
    main()
