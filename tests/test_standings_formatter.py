import unittest

from src.domain.models import MatchAggregate, MatchCore
from src.services.facts_formatter import FactsFormatter


class TestStandingsFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = FactsFormatter()
        self.match = MatchAggregate(
            core=MatchCore(
                id="1",
                home_team="Liverpool",
                away_team="Arsenal",
                competition="EPL",
                kickoff_jst="2026/02/23(月) 04:30 JST",
                kickoff_local="2026-02-22 19:30 Local",
            )
        )

    def test_format_standings_empty(self):
        self.formatter.format_standings(self.match, None)
        self.assertEqual(self.match.facts.standings_table, [])

        self.formatter.format_standings(self.match, [])
        self.assertEqual(self.match.facts.standings_table, [])

    def test_format_standings_success(self):
        raw_standings = [
            {
                "rank": 1,
                "team": {"id": 1, "name": "Liverpool", "logo": "logo1"},
                "points": 10,
                "all": {
                    "played": 5,
                    "win": 3,
                    "draw": 1,
                    "lose": 1,
                    "goals": {"for": 10, "against": 5},
                },
                "goalsDiff": 5,
                "form": "WWDLW",
                "description": "Champions League",
            },
            {
                "rank": 2,
                "team": {"id": 2, "name": "Arsenal", "logo": "logo2"},
                "points": 9,
                "all": {
                    "played": 5,
                    "win": 2,
                    "draw": 3,
                    "lose": 0,
                    "goals": {"for": 8, "against": 4},
                },
                "goalsDiff": 4,
                "form": "WDDWD",
                "description": "Champions League",
            },
        ]

        self.formatter.format_standings(self.match, raw_standings)
        table = self.match.facts.standings_table

        self.assertEqual(len(table), 2)
        self.assertEqual(table[0]["team_name"], "Liverpool")
        self.assertEqual(table[0]["rank"], 1)
        self.assertEqual(table[1]["team_name"], "Arsenal")
        self.assertEqual(table[1]["goals_for"], 8)
        self.assertEqual(table[1]["description"], "Champions League")


if __name__ == "__main__":
    unittest.main()
