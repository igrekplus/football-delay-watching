#!/usr/bin/env python3
"""
同国対決トリビアプロンプトテストスクリプト
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

# === テストデータ (Newcastle vs Manchester City の同国選手) ===
# スタメン・ベンチに実在する選手間の対決に限定
MATCHUP_CONTEXT = """
England: Lewis Hall (Newcastle), Anthony Gordon (Newcastle) vs Phil Foden (Manchester City), James Trafford (Manchester City)
Netherlands: Sven Botman (Newcastle) vs Nathan Ake (Manchester City)
"""


def main():
    print("=" * 60)
    print("同国対決トリビア プロンプトテスト")
    print("=" * 60)
    print(f"CONTEXT:\n{MATCHUP_CONTEXT.strip()}")
    print("-" * 60)

    # プロンプト構築
    prompt = build_prompt(
        "same_country_trivia",
        matchup_context=MATCHUP_CONTEXT,
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
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        raise


if __name__ == "__main__":
    main()
