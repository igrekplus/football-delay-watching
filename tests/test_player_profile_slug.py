import unittest

from src.utils.player_profile import build_player_profile_slug, build_player_profile_url


class TestPlayerProfileSlug(unittest.TestCase):
    def test_build_player_profile_slug(self):
        self.assertEqual(
            build_player_profile_slug(41621, "Matheus Nunes"), "41621-matheus-nunes"
        )
        self.assertEqual(
            build_player_profile_slug(41621, "R. Cherki"), "41621-r-cherki"
        )
        self.assertEqual(
            build_player_profile_slug(41621, "O'Hara\u0020\u0020"), "41621-o-hara"
        )
        self.assertEqual(build_player_profile_slug(41621, "---"), "41621-player")

    def test_build_player_profile_url(self):
        self.assertEqual(
            build_player_profile_url(41621, "Matheus Nunes"),
            "/player-profiles/41621-matheus-nunes.html",
        )


if __name__ == "__main__":
    unittest.main()
