import importlib.util
import os
import sys

# モジュールを直接ロード
file_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../src/utils/nationality_flags.py")
)
spec = importlib.util.spec_from_file_location("nationality_flags", file_path)
nationality_flags = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nationality_flags)

get_flag_emoji = nationality_flags.get_flag_emoji


def test_flags():
    test_cases = [
        ("Bulgaria", "🇧🇬"),
        ("Cyprus", "🇨🇾"),
        ("Côte d'Ivoire", "🇨🇮"),
        ("Cote D&#39;Ivoire", "🇨🇮"),  # HTML escaped
        ("Bosnia & Herzegovina", "🇧🇦"),
        ("Vietnam", "🇻🇳"),
        ("Curacao", "🇨🇼"),
        ("Angola", "🇦🇴"),
        ("South Korea", "🇰🇷"),  # Spaced -> Hyphenated
        ("South-Korea", "🇰🇷"),  # Hyphenated
        ("Republic of Ireland", "🇮🇪"),  # Alias
        ("North Macedonia", "🇲🇰"),  # Alias
        ("Bosnia and Herzegovina", "🇧🇦"),  # Alias
        ("Unknown Country", ""),
        ("", ""),
        (None, ""),
    ]

    failed = 0
    for country, expected in test_cases:
        result = get_flag_emoji(country)
        status = "✅" if result == expected else "❌"
        if result != expected:
            failed += 1
            print(f"{status} {country}: Expected '{expected}', got '{result}'")
        else:
            print(f"{status} {country}: '{result}'")

    if failed == 0:
        print("\nAll tests passed!")
    else:
        print(f"\n{failed} tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    test_flags()
