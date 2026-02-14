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

    def test_enrich_matches_fallback(self):
        # API returns error or empty
        self.mock_api.fetch_predictions.side_effect = Exception("API Error")
        self.mock_api.fetch_odds.return_value = {}

        # Should not raise exception
        self.service.enrich_matches([self.match])

        self.assertEqual(self.match.facts.prediction_percent, {})
        self.assertEqual(self.match.facts.scorer_odds, [])


if __name__ == "__main__":
    unittest.main()
