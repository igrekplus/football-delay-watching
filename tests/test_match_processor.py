import os
import unittest
from datetime import datetime
from unittest import mock

from src.match_processor import MatchProcessor


class TestMatchProcessor(unittest.TestCase):
    def test_target_fixture_id_fetches_only_explicit_fixture(self):
        processor = MatchProcessor()
        processor.client = mock.Mock()
        processor.client.fetch_fixtures.return_value = {
            "response": [{"league": {"id": 39, "name": "Premier League"}}]
        }
        processor.client.get_fixtures.side_effect = AssertionError(
            "date-based fetch should not run when TARGET_FIXTURE_ID is set"
        )

        sentinel_match = mock.Mock()

        with mock.patch.dict(os.environ, {"TARGET_FIXTURE_ID": "1379248"}):
            with mock.patch.object(
                processor, "_parse_match_data", return_value=sentinel_match
            ) as parse_match_data:
                matches = processor._fetch_matches_from_api()

        self.assertEqual(matches, [sentinel_match])
        processor.client.fetch_fixtures.assert_called_once_with(fixture_id="1379248")
        parse_match_data.assert_called_once()
        self.assertEqual(parse_match_data.call_args.args[1], "EPL")
        self.assertTrue(parse_match_data.call_args.kwargs["skip_time_window"])

    def test_parse_match_data_can_skip_time_window_for_explicit_fixture(self):
        processor = MatchProcessor()
        item = {
            "fixture": {
                "id": 1379248,
                "status": {"short": "FT"},
                "date": "2026-02-27T20:00:00+00:00",
                "venue": {"name": "Molineux Stadium", "city": "Wolverhampton"},
                "referee": "Test Ref",
            },
            "teams": {
                "home": {"name": "Wolves", "logo": "home.png"},
                "away": {"name": "Aston Villa", "logo": "away.png"},
            },
            "league": {
                "id": 39,
                "round": "Regular Season - 27",
                "logo": "league.png",
            },
        }

        with mock.patch.object(processor, "_is_within_time_window", return_value=False):
            match = processor._parse_match_data(
                item,
                "EPL",
                datetime(2026, 2, 27, 7, 0, 0),
                skip_time_window=True,
            )

        self.assertIsNotNone(match)
        self.assertEqual(match.id, "1379248")
        self.assertEqual(match.home_team, "Wolves")
        self.assertEqual(match.away_team, "Aston Villa")


if __name__ == "__main__":
    unittest.main()
