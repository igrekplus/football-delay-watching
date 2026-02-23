from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import pytz

from src.calendar_generator import CalendarGenerator
from src.utils.datetime_util import DateTimeUtil


class TestCalendarGenerator(TestCase):
    def setUp(self):
        self.generator = CalendarGenerator()
        self.generator.leagues = [
            {"id": 39, "name": "EPL", "display_name": "Premier League"}
        ]

    @patch("src.calendar_generator.get_calendar_info", return_value={})
    @patch("src.calendar_generator.datetime")
    def test_fetch_all_fixtures_uses_utc_week_range(
        self, mock_datetime, _mock_calendar
    ):
        fixed_now_utc = pytz.UTC.localize(datetime(2026, 2, 23, 12, 0, 0))
        fixed_now_jst = DateTimeUtil.to_jst(fixed_now_utc)
        mock_datetime.now.return_value = fixed_now_utc
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat

        fixtures = {
            "response": [
                self._fixture_item(1001, "2026-02-16T00:00:00Z"),  # start inclusive
                self._fixture_item(1002, "2026-02-15T23:59:59Z"),  # out (before start)
                self._fixture_item(1003, "2026-03-15T23:59:59Z"),  # end-1s inclusive
                self._fixture_item(1004, "2026-03-16T00:00:00Z"),  # out (end exclusive)
            ]
        }
        self.generator.api.get_fixtures = lambda _league_id, _season: fixtures

        with patch.object(DateTimeUtil, "now_jst", return_value=fixed_now_jst):
            all_fixtures = self.generator._fetch_all_fixtures()

        fixture_ids = {item["fixture_id"] for item in all_fixtures}
        self.assertIn(1001, fixture_ids)
        self.assertIn(1003, fixture_ids)
        self.assertNotIn(1002, fixture_ids)
        self.assertNotIn(1004, fixture_ids)

    @patch("src.calendar_generator.datetime")
    def test_build_timeline_groups_by_utc_monday_sunday(self, mock_datetime):
        fixed_now_utc = pytz.UTC.localize(datetime(2026, 2, 23, 12, 0, 0))
        mock_datetime.now.return_value = fixed_now_utc

        fixture_jst = DateTimeUtil.to_jst(
            pytz.UTC.localize(datetime(2026, 2, 22, 16, 30, 0))
        )
        fixtures = [
            {
                "fixture_id": 2001,
                "kickoff_jst": fixture_jst,
                "competition_name": "EPL",
            }
        ]

        weeks = self.generator._build_timeline(fixtures)

        self.assertEqual(weeks[0]["label"], "UTC 2/16(月) - 2/22(日)")
        self.assertIn("EPL", weeks[0]["leagues"])
        self.assertEqual(weeks[0]["leagues"]["EPL"][0]["fixture_id"], 2001)
        self.assertNotIn("EPL", weeks[1]["leagues"])

    @staticmethod
    def _fixture_item(fixture_id: int, date_iso: str) -> dict:
        return {
            "fixture": {
                "id": fixture_id,
                "date": date_iso,
                "timezone": "UTC",
                "venue": {"name": "Test Stadium"},
            },
            "teams": {
                "home": {"name": "Home", "logo": "home.png"},
                "away": {"name": "Away", "logo": "away.png"},
            },
            "league": {"logo": "league.png", "round": "Regular Season - 1"},
        }
