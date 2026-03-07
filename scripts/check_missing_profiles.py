import argparse
import csv
import logging
import os
import sys

# Add base path so we can import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.clients.api_football_client import ApiFootballClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def check_missing_profiles(fixture_id: str, team_id: str):
    try:
        client = ApiFootballClient()
        data = client.fetch_fixtures(fixture_id=fixture_id)

        responses = data.get("response", [])
        if not responses:
            logging.error(f"No data found for fixture {fixture_id}")
            sys.exit(1)

        fixture_data = responses[0]

        target_lineup = None
        for lineup in fixture_data.get("lineups", []):
            if str(lineup["team"]["id"]) == team_id:
                target_lineup = lineup
                break

        if not target_lineup:
            logging.error(
                f"Could not find lineup for team {team_id} in fixture {fixture_id}."
            )
            sys.exit(1)

        starters = target_lineup["startXI"]
        subs = target_lineup["substitutes"]

        # Determine CSV path
        csv_path = os.path.join("data", f"player_{team_id}.csv")
        if not os.path.exists(csv_path):
            logging.error(f"CSV file not found: {csv_path}")
            sys.exit(1)

        missing_set = set()
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row["profile_format"]:
                    missing_set.add(str(row["player_id"]))

        print(f"=== Missing Profiles for Team {team_id} in Fixture {fixture_id} ===")
        print("\n--- Starters ---")
        found_starters = False
        for s in starters:
            pid = str(s["player"]["id"])
            if pid in missing_set:
                print(f"ID: {pid}, Name: {s['player']['name']}")
                found_starters = True
        if not found_starters:
            print("No starters missing profiles.")

        print("\n--- Substitutes ---")
        found_subs = False
        for s in subs:
            pid = str(s["player"]["id"])
            if pid in missing_set:
                print(f"ID: {pid}, Name: {s['player']['name']}")
                found_subs = True
        if not found_subs:
            print("No substitutes missing profiles.")

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check for players missing profiles in a specific fixture and team lineup."
    )
    parser.add_argument(
        "--fixture-id", required=True, help="Fixture ID to check (e.g., 1523413)"
    )
    parser.add_argument("--team-id", required=True, help="Team ID to check (e.g., 50)")

    args = parser.parse_args()
    check_missing_profiles(args.fixture_id, args.team_id)
