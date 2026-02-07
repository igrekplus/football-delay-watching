import unittest
from datetime import datetime
from unittest.mock import patch

from src.domain.models import MatchAggregate, MatchCore
from src.services.facts_formatter import FactsFormatter


class TestFactsFormatterH2H(unittest.TestCase):
    def setUp(self):
        self.formatter = FactsFormatter()
        self.match = MatchAggregate(
            core=MatchCore(
                id="123",
                home_team="Liverpool",
                away_team="Man City",
                competition="EPL",
                kickoff_jst="2024-01-01 00:00",
                kickoff_local="2024-01-01 00:00",
                kickoff_at_utc=datetime(2024, 1, 1, 15, 0),
            )
        )

    def test_format_h2h_with_logos(self):
        # Sample API response
        api_data = {
            "response": [
                {
                    "fixture": {"date": "2023-12-01T15:00:00Z"},
                    "league": {"name": "Premier League", "logo": "league_logo_url"},
                    "teams": {
                        "home": {
                            "name": "Liverpool",
                            "id": 40,
                            "logo": "home_logo_url",
                        },
                        "away": {"name": "Man City", "id": 50, "logo": "away_logo_url"},
                    },
                    "goals": {"home": 3, "away": 2},
                }
            ]
        }

        with patch.dict("os.environ", {"TARGET_DATE": "2024-01-02"}):
            self.formatter.format_h2h(self.match, api_data, home_id=40)

        self.assertEqual(len(self.match.facts.h2h_details), 1)
        detail = self.match.facts.h2h_details[0]
        self.assertEqual(detail["league_logo"], "league_logo_url")
        self.assertEqual(detail["home_logo"], "home_logo_url")
        self.assertEqual(detail["away_logo"], "away_logo_url")
        self.assertEqual(detail["competition"], "Premier League")
        self.assertEqual(detail["result_key"], "W")

    def test_format_h2h_without_logos(self):
        # Sample API response without logos
        api_data = {
            "response": [
                {
                    "fixture": {"date": "2023-12-01T15:00:00Z"},
                    "league": {"name": "Premier League", "logo": None},
                    "teams": {
                        "home": {"name": "Liverpool", "id": 40, "logo": None},
                        "away": {"name": "Man City", "id": 50, "logo": None},
                    },
                    "goals": {"home": 2, "away": 2},
                }
            ]
        }

        from unittest.mock import patch

        with patch.dict("os.environ", {"TARGET_DATE": "2024-01-02"}):
            self.formatter.format_h2h(self.match, api_data, home_id=40)

        self.assertEqual(len(self.match.facts.h2h_details), 1)
        detail = self.match.facts.h2h_details[0]
        self.assertEqual(detail["league_logo"], "")
        self.assertEqual(detail["home_logo"], "")
        self.assertEqual(detail["away_logo"], "")
        self.assertEqual(detail["result_key"], "D")


if __name__ == "__main__":
    unittest.main()
