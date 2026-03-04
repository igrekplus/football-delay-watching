import unittest

from src.formatters.player_formatter import PlayerFormatter


class TestPlayerFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = PlayerFormatter()

    def test_format_injury_cards(self):
        injuries = [
            {"name": "S. Bajcetic", "team": "Liverpool", "reason": "Hamstring Injury"},
            {"name": "遠藤 航", "team": "Liverpool", "reason": "Injury"},
        ]
        player_nationalities = {"S. Bajcetic": "Spain", "遠藤 航": "Japan"}
        player_birthdates = {"S. Bajcetic": "2004-10-22", "遠藤 航": "1993-02-09"}

        result = self.formatter.format_injury_cards(
            injuries, {}, player_nationalities, player_birthdates
        )

        # Bajcetic
        self.assertIn("S. Bajcetic", result)
        self.assertIn("Spain", result)
        self.assertIn("🇪🇸", result)
        self.assertIn("2004/10/22", result)
        self.assertIn("⚠️ Hamstring Injury", result)

        # Endo
        self.assertIn("遠藤 航", result)
        self.assertIn("Japan", result)
        self.assertIn("🇯🇵", result)
        self.assertIn("1993/02/09", result)

    def test_format_player_cards(self):
        players = ["Kaoru Mitoma", "Son Heung-Min"]
        player_nationalities = {"Kaoru Mitoma": "Japan", "Son Heung-Min": "South Korea"}
        player_birthdates = {
            "Kaoru Mitoma": "1997-05-20",
            "Son Heung-Min": "1992-07-08",
        }
        player_numbers = {"Kaoru Mitoma": 22, "Son Heung-Min": 7}
        player_positions = {"Kaoru Mitoma": "F", "Son Heung-Min": "F"}
        player_instagram = {"Kaoru Mitoma": "insta1"}
        player_profiles = {"Son Heung-Min": {"format": "HTML", "detail": "Details"}}

        result = self.formatter.format_player_cards(
            players,
            "4-3-3",
            "Team A",
            player_nationalities,
            player_numbers,
            player_birthdates,
            None,
            player_positions,
            player_instagram,
            player_profiles,
        )

        self.assertIn("Kaoru Mitoma", result)
        self.assertIn("🇯🇵", result)
        self.assertIn("Son Heung-Min", result)
        self.assertIn("🇰🇷", result)


if __name__ == "__main__":
    unittest.main()
