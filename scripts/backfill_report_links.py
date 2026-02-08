import argparse
import json
import logging
import os

from settings.calendar_data_loader import load_all_calendar_data, update_report_link

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MANIFEST_PATH = "public/reports/manifest.json"


def backfill(dry_run=False):
    if not os.path.exists(MANIFEST_PATH):
        logger.error(f"Manifest file not found: {MANIFEST_PATH}")
        return

    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"Error loading manifest: {e}")
        return

    reports_by_date = manifest.get("reports_by_date", {})

    # fixture_id ごとの最新(最後に見つかった)レポートを収集
    latest_reports = {}  # fixture_id -> {file, competition, home_team, away_team, match_date}

    # 日付順に処理して後のもので上書きしていく
    dates = sorted(reports_by_date.keys())
    for date in dates:
        matches = reports_by_date[date].get("matches", [])
        for match in matches:
            fid = str(match.get("fixture_id"))
            filename = match.get("file")

            if fid and filename:
                latest_reports[fid] = {
                    "file": filename,
                    "competition": match.get("competition"),
                    "home_team": match.get("home_team"),
                    "away_team": match.get("away_team"),
                    "match_date": match.get("match_date")
                    or match.get("kickoff_local", "").split()[0],
                }

    logger.info(
        f"Found {len(latest_reports)} unique fixtures with reports in manifest."
    )

    calendar_data = load_all_calendar_data()
    updated_count = 0

    for fid, match_info in latest_reports.items():
        filename = match_info["file"]
        report_link = f"/reports/{filename}"

        # 現在の値を確認
        existing_info = calendar_data.get(fid)
        current_link = existing_info.get("report_link", "") if existing_info else ""

        if current_link != report_link:
            if dry_run:
                logger.info(
                    f"[DRY RUN] Would update/append fixture {fid}: {current_link} -> {report_link}"
                )
            else:
                success = update_report_link(
                    fid,
                    report_link,
                    league_name=match_info["competition"],
                    match_data={
                        "date_jst": match_info["match_date"],
                        "home_team": match_info["home_team"],
                        "away_team": match_info["away_team"],
                    },
                )
                if success:
                    updated_count += 1
                else:
                    logger.error(f"Failed to update fixture {fid}")
        else:
            logger.info(f"Fixture {fid} already has correct link: {report_link}")

    if dry_run:
        logger.info(f"Dry run complete. Found {len(latest_reports)} potential updates.")
    else:
        logger.info(f"Backfill complete. Updated/Appended {updated_count} fixtures.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill report links from manifest to calendar CSVs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without actually writing",
    )
    args = parser.parse_args()

    backfill(dry_run=args.dry_run)
