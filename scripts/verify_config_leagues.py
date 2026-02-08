from config import config


def test_config_leagues():
    print("--- League Info ---")
    print(f"TARGET_LEAGUES: {config.TARGET_LEAGUES}")
    print(f"LEAGUE_IDS: {config.LEAGUE_IDS}")

    expected_leagues = ["EPL", "CL", "LALIGA", "FA", "COPA", "EFL"]
    for league in expected_leagues:
        if league not in config.TARGET_LEAGUES:
            print(f"FAILED: {league} not in TARGET_LEAGUES")
            return

    print("SUCCESS: All leagues found in TARGET_LEAGUES")

    if config.LEAGUE_IDS.get("EPL") == 39:
        print("SUCCESS: EPL ID is correct (39)")
    else:
        print(f"FAILED: EPL ID is {config.LEAGUE_IDS.get('EPL')}")

    if hasattr(config, "LEAGUE_INFO") and len(config.LEAGUE_INFO) > 0:
        print(f"SUCCESS: LEAGUE_INFO contains {len(config.LEAGUE_INFO)} entries")
    else:
        print("FAILED: LEAGUE_INFO is missing or empty")


if __name__ == "__main__":
    test_config_leagues()
