#!/usr/bin/env python3
"""
戦術プレビュープロンプトテストスクリプト
現行プロンプトの動作確認・リファクタ後の品質検証用

データソース: https://football-delay-watching-a8830.web.app/reports/2026-01-13_Newcastle_vs_ManchesterCity_20260115_220154.html
"""

import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import config  # noqa: E402
from settings.gemini_prompts import build_prompt  # noqa: E402
from src.clients.gemini_rest_client import GeminiRestClient  # noqa: E402

# === テストデータ (Newcastle vs Manchester City, EFL Cup 2026-01-13) ===
HOME_TEAM = "Newcastle"
AWAY_TEAM = "Manchester City"
HOME_FORMATION = "4-3-3"
AWAY_FORMATION = "4-1-4-1"

# Newcastle スタメン (Starting XI)
HOME_LINEUP = (
    "Nick Pope, Lewis Miley, Malick Thiaw, Sven Botman, Lewis Hall, "
    "Jacob Ramsey, Bruno Guimaraes, Joelinton, Jacob Murphy, Yoane Wissa, Anthony Gordon"
)

# Manchester City スタメン (Starting XI)
AWAY_LINEUP = (
    "James Trafford, Matheus Nunes, Abdukodir Khusanov, Max Alleyne, Nathan Ake, "
    "Nico O'Reilly, Antoine Semenyo, Bernardo Silva, Phil Foden, Jeremy Doku, Erling Haaland"
)

COMPETITION = "EFL Cup"


def main():
    print("=" * 60)
    print("戦術プレビュー プロンプトテスト")
    print("=" * 60)
    print(f"HOME: {HOME_TEAM} ({HOME_FORMATION})")
    print(f"AWAY: {AWAY_TEAM} ({AWAY_FORMATION})")
    print("-" * 60)

    # プロンプト構築
    prompt = build_prompt(
        "tactical_preview",
        home_team=HOME_TEAM,
        away_team=AWAY_TEAM,
        home_formation=HOME_FORMATION,
        away_formation=AWAY_FORMATION,
        home_lineup=HOME_LINEUP,
        away_lineup=AWAY_LINEUP,
        competition=COMPETITION,
    )

    print("📝 生成されたプロンプト:")
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
        print(f"\n文字数: {len(result)}")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        raise


if __name__ == "__main__":
    main()
