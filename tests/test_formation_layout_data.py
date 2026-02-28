import unittest

from src.utils.formation_image import get_formation_layout_data
from src.utils.nationality_flags import get_flagcdn_country_code


class TestFormationLayoutData(unittest.TestCase):
    def test_get_flagcdn_country_code_uses_shared_nationality_mapping(self):
        self.assertEqual(get_flagcdn_country_code("Ghana"), "gh")
        self.assertEqual(get_flagcdn_country_code("Algeria"), "dz")
        self.assertEqual(get_flagcdn_country_code("England"), "gb-eng")

    def test_blank_short_name_falls_back_to_manual_abbreviation(self):
        layout = get_formation_layout_data(
            formation="4-3-3",
            players=["Marc Guéhi"],
            team_name="Manchester City",
            team_logo="",
            team_color="#000000",
            is_home=True,
            player_nationalities={"Marc Guéhi": "England"},
            player_numbers={},
            player_photos={},
            player_short_names={"Marc Guéhi": ""},
        )

        player = layout["players"][0]
        self.assertEqual(player["short_name"], "M. Guéhi")
        self.assertEqual(player["nationality"], "gb-eng")
        self.assertEqual(player["flag_url"], "https://flagcdn.com/gb-eng.svg")


if __name__ == "__main__":
    unittest.main()
