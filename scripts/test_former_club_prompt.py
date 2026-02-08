#!/usr/bin/env python3
"""
古巣対決プロンプト/パーサー 統合テストスクリプト
LLM出力 -> クリーンアップ -> パース -> HTML生成 の全工程を検証
"""

import os
import re
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config import config  # noqa: E402
from settings.gemini_prompts import build_prompt  # noqa: E402
from src.clients.gemini_rest_client import GeminiRestClient  # noqa: E402
from src.formatters.matchup_formatter import MatchupFormatter  # noqa: E402
from src.parsers.former_club_parser import parse_former_club_text  # noqa: E402

# === テストデータ (Newcastle vs Manchester City, EFL Cup 2026-01-13) ===
HOME_TEAM = "Newcastle"
AWAY_TEAM = "Manchester City"
MATCH_DATE = "2026-01-13"

# スタメン・ベンチから抽出
HOME_PLAYERS = [
    "Nick Pope",
    "Lewis Miley",
    "Malick Thiaw",
    "Sven Botman",
    "Lewis Hall",
    "Jacob Ramsey",
    "Bruno Guimaraes",
    "Joelinton",
    "Jacob Murphy",
    "Yoane Wissa",
    "Anthony Gordon",
    "Aaron Ramsdale",
    "Kieran Trippier",
    "Alex Murphy",
    "Sandro Tonali",
    "Antony Elanga",
    "Joe Willock",
    "Harvey Barnes",
    "Nick Woltemade",
    "Sean Neave",
]

AWAY_PLAYERS = [
    "James Trafford",
    "Matheus Nunes",
    "Abdukodir Khusanov",
    "Max Alleyne",
    "Nathan Ake",
    "Nico O'Reilly",
    "Antoine Semenyo",
    "Bernardo Silva",
    "Phil Foden",
    "Jeremy Doku",
    "Erling Haaland",
    "Gianluigi Donnarumma",
    "Rico Lewis",
    "Rayan Cherki",
    "Rayan Ait-Nouri",
    "Rodri",
    "Charlie Gray",
    "Divine Mukasa",
    "Tijjani Reijnders",
    "Ryan McAidoo",
]


def main():
    print("=" * 60)
    print("古巣対決 プロンプト/パーサー 統合テスト")
    print("=" * 60)
    print(f"HOME: {HOME_TEAM}")
    print(f"AWAY: {AWAY_TEAM}")
    print(f"DATE: {MATCH_DATE}")
    print("-" * 60)

    # 1. プロンプト構築
    prompt = build_prompt(
        "former_club_trivia",
        home_team=HOME_TEAM,
        away_team=AWAY_TEAM,
        home_players=", ".join(HOME_PLAYERS),
        away_players=", ".join(AWAY_PLAYERS),
        match_date=MATCH_DATE,
    )

    print("📝 生成されたプロンプト (一部):")
    print("-" * 60)
    print("\n".join(prompt.split("\n")[:10]) + "\n...")
    print("-" * 60)

    # 2. API呼び出し
    print("\n🔍 Gemini Grounding API を呼び出し中...")
    client = GeminiRestClient(api_key=config.GOOGLE_API_KEY)

    try:
        raw_result = client.generate_content_with_grounding(prompt)
        print("\n✅ API Raw Response 取得完了")

        # 3. 出典番号削除 (TributeGenerator と同じ処理)
        cleaned_result = (
            re.sub(r"\s*\[\d+(?:,\s*\d+)*\]", "", raw_result) if raw_result else ""
        )
        print("\n📝 クリーンアップ後の出力:")
        print("-" * 60)
        print(cleaned_result)
        print("-" * 60)

        # 4. パース
        print("\n🔍 パース実行中...")
        entries = parse_former_club_text(cleaned_result, HOME_TEAM, AWAY_TEAM)

        print(f"\n✅ 抽出されたエントリ数: {len(entries)}")
        for i, entry in enumerate(entries):
            print(f"  [{i + 1}] {entry.name} ({entry.team})")
            print(f"      {entry.description[:100]}...")

        # 5. HTML生成
        print("\n🎨 HTML生成中...")
        formatter = MatchupFormatter()
        # テスト用なので選手写真やロゴは空の辞書を渡す
        html = formatter.format_former_club_section(entries, {}, {})

        # 6. ファイル出力
        os.makedirs("tmp", exist_ok=True)
        output_path = "tmp/former_club_test_output.html"

        # 簡易的なHTMLテンプレートを被せる
        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Former Club Test Output</title>
    <style>
        body {{ font-family: sans-serif; background: #f0f2f5; padding: 20px; }}
        .matchup-section {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section-title {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
        .matchup-container {{ display: flex; flex-direction: column; gap: 10px; }}
        .matchup-country {{ border: 1px solid #ddd; padding: 15px; border-radius: 4px; }}
        .matchup-player-name {{ font-weight: bold; font-size: 1.1em; }}
        .matchup-team-name {{ color: #666; font-size: 0.9em; }}
        .matchup-description {{ margin-top: 10px; color: #333; line-height: 1.5; }}
    </style>
</head>
<body>
    <h1>Former Club Test Output</h1>
    <p>試合: {HOME_TEAM} vs {AWAY_TEAM} ({MATCH_DATE})</p>
    <hr>
    {html}
    <hr>
    <h3>RAW LLM Output (Cleaned)</h3>
    <pre style="background: #eee; padding: 10px; white-space: pre-wrap;">{cleaned_result}</pre>
</body>
</html>
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_html)

        print(f"\n✨ テスト結果を保存しました: {os.path.abspath(output_path)}")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
