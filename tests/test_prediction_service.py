from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.domain.models import MatchAggregate, MatchCore
from src.prediction_service import PredictionService


class TestPredictionService(unittest.TestCase):
    def setUp(self):
        self.mock_api = MagicMock()
        self.service = PredictionService(api_client=self.mock_api)

        # Test match
        core = MatchCore(
            id="123",
            home_team="Team A",
            away_team="Team B",
            competition="Premier League",
            kickoff_jst="2025-01-01",
            kickoff_local="2025-01-01 20:00 Local",
            is_target=True,
        )
        self.match = MatchAggregate(core=core)

    def test_enrich_matches_predictions(self):
        # Mock API response for predictions
        self.mock_api.fetch_predictions.return_value = {
            "response": [
                {
                    "predictions": {
                        "percent": {"home": "50%", "draw": "20%", "away": "30%"}
                    }
                }
            ]
        }
        self.mock_api.fetch_odds.return_value = {"response": []}

        self.service.enrich_matches([self.match])

        self.assertEqual(self.match.facts.prediction_percent["home"], "50%")
        self.assertEqual(self.match.facts.prediction_percent["draw"], "20%")
        self.assertEqual(self.match.facts.prediction_percent["away"], "30%")

    def test_enrich_matches_odds_filtering(self):
        # Mock API response for odds
        self.mock_api.fetch_predictions.return_value = {"response": []}
        self.mock_api.fetch_odds.return_value = {
            "response": [
                {
                    "bookmakers": [
                        {
                            "bets": [
                                {
                                    "name": "Anytime Goal Scorer",
                                    "values": [
                                        {"value": "Player 1", "odd": "1.50"},
                                        {"value": "Player 2", "odd": "2.00"},
                                        {"value": "Player 3", "odd": "2.50"},
                                        {"value": "Player 4", "odd": "3.00"},
                                        {"value": "Player 5", "odd": "3.50"},
                                        {
                                            "value": "Player 6",
                                            "odd": "4.00",
                                        },  # Should be filtered out
                                    ],
                                },
                                {
                                    "name": "Match Winner",  # Should be ignored
                                    "values": [{"value": "Home", "odd": "2.00"}],
                                },
                            ]
                        }
                    ]
                }
            ]
        }

        self.service.enrich_matches([self.match])

        self.assertEqual(len(self.match.facts.scorer_odds), 1)
        market = self.match.facts.scorer_odds[0]
        self.assertEqual(market["market"], "Anytime Goal Scorer")
        self.assertEqual(len(market["values"]), 5)
        self.assertEqual(market["values"][0]["player"], "Player 1")
        self.assertEqual(market["values"][4]["player"], "Player 5")

    def test_enrich_matches_odds_sorting(self):
        # Mock API response for odds with unsorted values and invalid entries
        self.mock_api.fetch_predictions.return_value = {"response": []}
        self.mock_api.fetch_odds.return_value = {
            "response": [
                {
                    "bookmakers": [
                        {
                            "bets": [
                                {
                                    "name": "Anytime Goal Scorer",
                                    "values": [
                                        {"value": "Player High", "odd": "10.00"},
                                        {"value": "Player Mid", "odd": "5.00"},
                                        {"value": "Player Low", "odd": "1.10"},
                                        {"value": "Invalid", "odd": "invalid"},
                                        {"value": "Empty", "odd": ""},
                                        {"value": "None", "odd": None},
                                        {"value": "Player Top", "odd": "1.05"},
                                        {"value": "Player 5th", "odd": "15.00"},
                                        {"value": "Player 6th", "odd": "20.00"},
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        self.service.enrich_matches([self.match])

        self.assertEqual(len(self.match.facts.scorer_odds), 1)
        market = self.match.facts.scorer_odds[0]
        values = market["values"]

        # 期待される順序: Player Top (1.05), Player Low (1.10), Player Mid (5.00), Player High (10.00), Player 5th (15.00)
        # Player 6th は6番目、Invalidなどは除外されるため入らないはず
        self.assertEqual(len(values), 5)
        self.assertEqual(values[0]["player"], "Player Top")
        self.assertEqual(values[0]["odd"], "1.05")
        self.assertEqual(values[1]["player"], "Player Low")
        self.assertEqual(values[2]["player"], "Player Mid")
        self.assertEqual(values[3]["player"], "Player High")
        self.assertEqual(values[4]["player"], "Player 5th")

    def test_enrich_matches_odds_fewer_than_five(self):
        # 5件未満の場合のテスト
        self.mock_api.fetch_predictions.return_value = {"response": []}
        self.mock_api.fetch_odds.return_value = {
            "response": [
                {
                    "bookmakers": [
                        {
                            "bets": [
                                {
                                    "name": "First Goal Scorer",
                                    "values": [
                                        {"value": "P2", "odd": "2.50"},
                                        {"value": "P1", "odd": "1.50"},
                                    ],
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        self.service.enrich_matches([self.match])
        market = self.match.facts.scorer_odds[0]
        values = market["values"]

        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]["player"], "P1")
        self.assertEqual(values[1]["player"], "P2")


if __name__ == "__main__":
    unittest.main()
