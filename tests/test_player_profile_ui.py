import unittest

from src.formatters.player_formatter import PlayerFormatter
from src.utils.formation_image import get_formation_layout_data


class TestPlayerProfileUi(unittest.TestCase):
    def test_player_cards_include_profile_url_data_attribute(self):
        formatter = PlayerFormatter()

        # Test with profile URL
        html = formatter.format_player_cards(
            lineup=["R. Cherki"],
            formation="4-3-3",
            team_name="Manchester City",
            player_photos={"R. Cherki": "https://example.com/cherki.png"},
            player_profile_urls={"R. Cherki": "/player-profiles/156477.html"},
        )

        # Static HTML should ONLY have the data attribute. Badge/Classes are added by JS.
        self.assertIn('data-player-profile-url="/player-profiles/156477.html"', html)
        self.assertIn('data-player-photo="https://example.com/cherki.png"', html)
        # Class and badge are now added dynamically by JS, so they shouldn't be in static HTML
        self.assertNotIn("player-card-profile-available", html)
        self.assertNotIn("player-profile-badge", html)

    def test_formation_layout_data_includes_profile_url(self):
        layout = get_formation_layout_data(
            formation="4-3-3",
            players=["R. Cherki"],
            team_name="Manchester City",
            team_logo="",
            team_color="#000000",
            is_home=True,
            player_nationalities={"R. Cherki": "France"},
            player_numbers={"R. Cherki": 10},
            player_photos={},
            player_profile_urls={"R. Cherki": "/player-profiles/156477.html"},
        )

        player = layout["players"][0]
        self.assertEqual(player["profile_url"], "/player-profiles/156477.html")
        self.assertNotIn("has_profile", player)
        self.assertNotIn("profile_id", player)


if __name__ == "__main__":
    unittest.main()
