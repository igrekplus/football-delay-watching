import csv
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# プロジェクトルートからの相対パス (Issue #192)
CACHE_DIR = Path(__file__).parent.parent.parent / "settings" / "standings"
CACHE_FILE = CACHE_DIR / "standings_cache.csv"

# Standard CSV Headers
HEADERS = [
    "week_key",
    "league",
    "rank",
    "team_id",
    "team_name",
    "team_logo",
    "points",
    "played",
    "won",
    "draw",
    "lost",
    "goals_for",
    "goals_against",
    "goals_diff",
    "form",
    "description",
]


def get_week_key(match_date: datetime) -> str:
    """
    Get the week key (Monday-based YYYY-MM-DD) for a given date.
    JST Monday is the start of the week.
    """
    # match_date should be JST
    # weekday: Monday=0, Sunday=6
    monday = match_date - timedelta(days=match_date.weekday())
    return monday.strftime("%Y-%m-%d")


def has_standings(week_key: str, league: str) -> bool:
    """Check if standings data exists for the given week and league."""
    if not os.path.exists(CACHE_FILE):
        return False

    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("week_key") == week_key and row.get("league") == league:
                    return True
    except Exception as e:
        logger.error(f"Error reading standings cache: {e}")

    return False


def save_standings(week_key: str, league: str, standings: list[dict]):
    """Save standings data to the CSV cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    file_exists = CACHE_FILE.exists()

    try:
        # Append to the file
        with open(CACHE_FILE, mode="a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            if not file_exists:
                writer.writeheader()

            for entry in standings:
                row = {
                    "week_key": week_key,
                    "league": league,
                    "rank": entry.get("rank"),
                    "team_id": entry.get("team", {}).get("id"),
                    "team_name": entry.get("team", {}).get("name"),
                    "team_logo": entry.get("team", {}).get("logo"),
                    "points": entry.get("points"),
                    "played": entry.get("all", {}).get("played"),
                    "won": entry.get("all", {}).get("win"),
                    "draw": entry.get("all", {}).get("draw"),
                    "lost": entry.get("all", {}).get("lose"),
                    "goals_for": entry.get("all", {}).get("goals", {}).get("for"),
                    "goals_against": entry.get("all", {})
                    .get("goals", {})
                    .get("against"),
                    "goals_diff": entry.get("goalsDiff"),
                    "form": entry.get("form"),
                    "description": entry.get("description", ""),
                }
                writer.writerow(row)
        logger.info(f"Saved standings cache for {league} {week_key}")
    except Exception as e:
        logger.error(f"Error saving standings cache: {e}")


def load_standings(week_key: str, league: str) -> list[dict]:
    """Load standings data from the CSV cache."""
    results = []
    if not os.path.exists(CACHE_FILE):
        return results

    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("week_key") == week_key and row.get("league") == league:
                    # Convert back to expected format for formatter
                    results.append(
                        {
                            "rank": int(row["rank"]),
                            "team": {
                                "id": int(row["team_id"]),
                                "name": row["team_name"],
                                "logo": row["team_logo"],
                            },
                            "points": int(row["points"]),
                            "all": {
                                "played": int(row["played"]),
                                "win": int(row["won"]),
                                "draw": int(row["draw"]),
                                "lose": int(row["lost"]),
                                "goals": {
                                    "for": int(row["goals_for"]),
                                    "against": int(row["goals_against"]),
                                },
                            },
                            "goalsDiff": int(row["goals_diff"]),
                            "form": row["form"],
                            "description": row["description"],
                        }
                    )
    except Exception as e:
        logger.error(f"Error loading standings cache: {e}")

    return results
