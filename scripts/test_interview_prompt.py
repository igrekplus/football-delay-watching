#!/usr/bin/env python3
"""
監督インタビュープロンプトテストスクリプト
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
TEAM_NAME = "Newcastle"
MANAGER_NAME = "Eddie Howe"
MATCH_INFO = "Newcastle vs Manchester City (EFL Cup)"
OPPONENT_TEAM = "Manchester City"
OPPONENT_MANAGER_NAME = "Pep Guardiola"


def main():
    print("=" * 60)
    print("監督インタビュー プロンプトテスト")
    print("=" * 60)
    print(f"TEAM: {TEAM_NAME} (Manager: {MANAGER_NAME})")
    print(f"MATCH: {MATCH_INFO}")
    print("-" * 60)

    # プロンプト構築
    prompt = build_prompt(
        "interview",
        team_name=TEAM_NAME,
        manager_name=MANAGER_NAME,
        match_info=MATCH_INFO,
        opponent_team=OPPONENT_TEAM,
        opponent_manager_name=OPPONENT_MANAGER_NAME,
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
