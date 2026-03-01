import unittest

from src.formatters.player_formatter import PlayerFormatter
from src.utils.formation_image import get_formation_layout_data


class TestPlayerProfileUi(unittest.TestCase):
    def test_player_cards_include_profile_trigger_for_profiled_players_only(self):
        formatter = PlayerFormatter()

        html = formatter.format_player_cards(
            lineup=["R. Cherki"],
            formation="4-3-3",
            team_name="Manchester City",
            player_photos={"R. Cherki": "https://example.com/cherki.png"},
            player_profiles={
                "R. Cherki": {
                    "format": "labelled_lines_v1",
                    "detail": "生まれ::フランス・リヨン",
                }
            },
        )

        self.assertIn('class="player-card player-card-profile-available"', html)
        self.assertIn('class="player-profile-badge"', html)
        self.assertIn('data-player-profile-id="player-profile-r-cherki"', html)
        self.assertIn('data-player-photo="https://example.com/cherki.png"', html)
        self.assertNotIn("タップで詳細", html)

        html_without_profile = formatter.format_player_cards(
            lineup=["Rodri"],
            formation="4-3-3",
            team_name="Manchester City",
            player_profiles={},
        )

        self.assertNotIn('class="player-profile-badge"', html_without_profile)
        self.assertNotIn(
            'data-player-profile-id="player-profile-rodri"', html_without_profile
        )

    def test_formation_layout_data_marks_profile_availability(self):
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
            player_profiles={
                "R. Cherki": {
                    "format": "labelled_lines_v1",
                    "detail": "生まれ::フランス・リヨン",
                }
            },
        )

        player = layout["players"][0]
        self.assertTrue(player["has_profile"])
        self.assertEqual(player["profile_id"], "player-profile-r-cherki")


if __name__ == "__main__":
    unittest.main()
