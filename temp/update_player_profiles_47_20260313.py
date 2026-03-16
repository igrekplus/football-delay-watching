import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data/player_47.csv"

PROFILE_FILES = {
    "265826": PROJECT_ROOT
    / "temp/player_profiles_20260313_tottenham_antonin_kinsky.md",
    "25287": PROJECT_ROOT / "temp/player_profiles_20260313_tottenham_kevin_danso.md",
    "328089": PROJECT_ROOT / "temp/player_profiles_20260313_tottenham_archie_gray.md",
    "270510": PROJECT_ROOT / "temp/player_profiles_20260313_tottenham_mathys_tel.md",
    "21104": PROJECT_ROOT
    / "temp/player_profiles_20260313_tottenham_randal_kolo_muani.md",
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
