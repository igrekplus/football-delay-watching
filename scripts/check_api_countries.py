import importlib.util
import json
import os

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def fetch_and_check_countries():
    api_key = os.getenv("API_FOOTBALL_KEY")
    if not api_key:
        print("Error: API_FOOTBALL_KEY not found in environment variables.")
        return

    print("Fetching countries from API-Football...")

    url = "https://v3.football.api-sports.io/countries"
    headers = {"x-apisports-key": api_key}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    if "response" not in data:
        print("Error: Invalid response format from API.")
        print(data)
        return

    api_countries = data["response"]
    print(f"Fetched {len(api_countries)} countries from API.")

    # 現在の辞書をロード
    file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../src/utils/nationality_flags.py")
    )
    spec = importlib.util.spec_from_file_location("nationality_flags", file_path)
    nationality_flags = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nationality_flags)

    current_flags = nationality_flags.NATIONALITY_FLAGS

    missing_countries = []

    print("\n--- Examining Countries ---")
    for item in api_countries:
        country_name = item.get("name")
        if not country_name:
            continue

        # 既に辞書にあるかチェック
        emoji = current_flags.get(country_name)
        if not emoji:
            # HTMLエスケープされている可能性も考慮 (APIからの生データには通常含まれないが、念のため)
            import html

            decoded = html.unescape(country_name)
            if current_flags.get(decoded):
                continue

            # 国名コード(code)がある場合は参考情報として表示
            code = item.get("code")
            missing_countries.append({"name": country_name, "code": code})
            # print(f"Missing: {country_name} ({code})")

    print(f"\nTotal Missing Countries: {len(missing_countries)}")

    # 不足リストを保存
    output_file = os.path.join(os.path.dirname(__file__), "missing_countries.json")
    with open(output_file, "w") as f:
        json.dump(missing_countries, f, indent=2, ensure_ascii=False)
    print(f"Saved missing countries to {output_file}")


if __name__ == "__main__":
    fetch_and_check_countries()
