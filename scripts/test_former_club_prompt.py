#!/usr/bin/env python3
"""
Gemini Grounding API 直接テストスクリプト
古巣対決プロンプトのデバッグ用
"""

import os
import sys

# プロジェクトルートをパスに追加（scripts/ の親ディレクトリ）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import config  # noqa: E402
from settings.gemini_prompts import build_prompt  # noqa: E402
from src.clients.gemini_rest_client import GeminiRestClient  # noqa: E402

# テストデータ
HOME_TEAM = "Manchester City"
AWAY_TEAM = "Exeter City"
MATCH_DATE = "2026-01-10"

# Man City vs Exeter City のスタメン・ベンチ（実際のデータ）
HOME_PLAYERS = [
    "Stefan Ortega",
    "James Trafford",
    "Kyle Walker",
    "Ruben Dias",
    "Nathan Ake",
    "Josko Gvardiol",
    "Rico Lewis",
    "John Stones",
    "Max Alleyne",
    "Manuel Akanji",
    "Rodri",
    "Jack Grealish",
    "Phil Foden",
    "Kevin De Bruyne",
    "James McAtee",
    "Divin Mubama",
    "Erling Haaland",
    "Oscar Bobb",
    "Savinho",
]

AWAY_PLAYERS = [
    "Joe Whitworth",
    "Joe Young",
    "Ilmari Niskanen",
    "Pierce Sweeney",
    "Ed Turns",
    "Johnly Yfeko",
    "Jack Sherring",
    "Josh Key",
    "Reece Cole",
    "Jack Aitchison",
    "Caleb Sherring",
    "Cameron Dawson",
    "Tristan Crama",
    "Jake Doyle-Hayes",
    "Migue Sherring",
    "Preslav Sherring",
    "Dara Sherring",
]


def main():
    print("=" * 60)
    print("Gemini Grounding API 直接テスト")
    print("=" * 60)
    print(f"HOME: {HOME_TEAM}")
    print(f"AWAY: {AWAY_TEAM}")
    print(f"DATE: {MATCH_DATE}")
    print("-" * 60)

    # プロンプト構築
    prompt = build_prompt(
        "former_club_trivia",
        home_team=HOME_TEAM,
        away_team=AWAY_TEAM,
        home_players=", ".join(HOME_PLAYERS),
        away_players=", ".join(AWAY_PLAYERS),
        match_date=MATCH_DATE,
    )

    print("\n📝 生成されたプロンプト:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)

    # API呼び出し
    print("\n🔍 Gemini Grounding API を呼び出し中...")
    client = GeminiRestClient(api_key=config.GOOGLE_API_KEY)

    try:
        result = client.generate_content_with_grounding(prompt)
        print("\n✅ API応答:")
        print("=" * 60)
        print(result)
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        raise


if __name__ == "__main__":
    main()
