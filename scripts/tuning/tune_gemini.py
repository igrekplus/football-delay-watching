#!/usr/bin/env python3
"""
Geminiプロンプトチューニングツール

ニュース要約、戦術プレビュー、ネタバレチェックのプロンプトを調整する。

Usage:
    python scripts/tuning/tune_gemini.py summary --articles-file articles.json --home "Man City" --away "West Ham"
    python scripts/tuning/tune_gemini.py preview --articles-file articles.json --home "Man City" --away "West Ham"
    python scripts/tuning/tune_gemini.py spoiler --text "City won 3-1" --home "Man City" --away "West Ham"
"""

import argparse
import json
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from dotenv import load_dotenv

from src.clients.llm_client import LLMClient


def print_header(title: str):
    """ヘッダーを表示"""
    print("=" * 80)
    print(title)
    print("=" * 80)


def load_articles(path: str) -> list[dict]:
    """記事JSONを読み込む"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # リスト形式をそのまま返す
    if isinstance(data, list):
        return data

    # 他の形式の場合
    return data.get("articles", data.get("kept", []))


def print_articles_context(
    articles: list[dict], max_articles: int = 3, max_chars: int = 500
):
    """記事コンテキストのプレビューを表示"""
    context_preview = "\n".join(
        [a.get("content", "")[:100] for a in articles[:max_articles]]
    )
    print(f"\nContext preview (first {max_articles} articles):")
    print("-" * 40)
    print(context_preview[:max_chars] + "...")
    print("-" * 40)


def cmd_summary(args):
    """summaryサブコマンド: ニュース要約をテスト"""
    load_dotenv()

    if not args.articles_file:
        print("ERROR: --articles-file is required")
        return 1

    articles = load_articles(args.articles_file)
    if not articles:
        print("ERROR: No articles found in file")
        return 1

    print_header(f"GEMINI SUMMARY | {args.home} vs {args.away}")
    print(f"Input: {len(articles)} articles from {args.articles_file}")

    # プロンプト表示
    print_articles_context(articles)

    print("\nPrompt template (from llm_client.py):")
    print(
        "  Task: Summarize news snippets into Japanese pre-match summary (600-1000 chars)"
    )
    print("  Constraints: Do NOT reveal results, no AI preamble")
    print("-" * 40)

    # 生成実行
    client = LLMClient(use_mock=args.mock)

    print("\n--- Generated Output ---")
    try:
        result = client.generate_news_summary(
            home_team=args.home,
            away_team=args.away,
            articles=articles,
        )
        print(result)
        print(f"\n(Length: {len(result)} chars)")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    print("--- End ---")

    print("\n" + "=" * 80)
    print("Tip: プロンプトを変更するには src/clients/llm_client.py を編集")
    print("=" * 80)

    return 0


def cmd_preview(args):
    """previewサブコマンド: 戦術プレビューをテスト"""
    load_dotenv()

    if not args.articles_file:
        print("ERROR: --articles-file is required")
        return 1

    articles = load_articles(args.articles_file)
    if not articles:
        print("ERROR: No articles found in file")
        return 1

    print_header(f"GEMINI TACTICAL PREVIEW | {args.home} vs {args.away}")
    print(f"Input: {len(articles)} articles from {args.articles_file}")

    # Sample formation/lineup data for testing (defaults)
    # 実際の選手名を使用 (Sunderland vs Man City sample)
    home_formation = args.home_formation or "4-2-3-1"
    away_formation = args.away_formation or "4-3-2-1"

    # Parse lineups from args (comma separated) or use defaults
    if args.home_lineup:
        home_lineup = [x.strip() for x in args.home_lineup.split(",")]
    else:
        home_lineup = [
            "Roefs",
            "Hume",
            "Mukiele",
            "Alderete",
            "Cirkin",
            "Xhaka",
            "Geertruida",
            "Le Fee",
            "Mayenda",
            "Adingra",
            "Brobbey",
        ]

    if args.away_lineup:
        away_lineup = [x.strip() for x in args.away_lineup.split(",")]
    else:
        away_lineup = [
            "Donnarumma",
            "Nunes",
            "Dias",
            "Aké",
            "O'Reilly",
            "Nico",
            "Bernardo",
            "Foden",
            "Cherki",
            "Haaland",
            "Savinho",
        ]

    competition = args.competition or "Premier League"

    print("\nFormation Data:")
    print(f"  Home: {home_formation} | Away: {away_formation}")
    print(f"  Competition: {competition}")
    print("-" * 40)

    print("\nPrompt template (from settings/gemini_prompts.py):")
    print("  Task: Structured tactical preview with 3 sections")
    print("  Constraints: Use input formation data, no hallucination")
    print("-" * 40)

    # 生成実行
    client = LLMClient(use_mock=args.mock)

    print("\n--- Generated Output ---")
    try:
        result = client.generate_tactical_preview(
            home_team=args.home,
            away_team=args.away,
            articles=articles,
            home_formation=home_formation,
            away_formation=away_formation,
            home_lineup=home_lineup,
            away_lineup=away_lineup,
            competition=competition,
        )
        print(result)
        print(f"\n(Length: {len(result)} chars)")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    print("--- End ---")

    print("\n" + "=" * 80)
    print("Tip: プロンプトを変更するには settings/gemini_prompts.py を編集")
    print("=" * 80)

    return 0


def cmd_spoiler(args):
    """spoilerサブコマンド: ネタバレチェックをテスト"""
    load_dotenv()

    if not args.text:
        print("ERROR: --text is required")
        return 1

    print_header(f"GEMINI SPOILER CHECK | {args.home} vs {args.away}")
    print(f"Input text: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")

    print("\nPrompt template (from llm_client.py):")
    print("  判定基準: スコア(2-1等), 勝敗(won/lost等), ゴール決めた選手名")
    print("  出力: JSON {is_safe: bool, reason: string}")
    print("-" * 40)

    # チェック実行
    client = LLMClient(use_mock=args.mock)

    print("\n--- Check Result ---")
    try:
        is_safe, reason = client.check_spoiler(
            text=args.text,
            home_team=args.home,
            away_team=args.away,
        )

        if is_safe:
            print("✅ SAFE: ネタバレなし")
        else:
            print(f"❌ SPOILER DETECTED: {reason}")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    print("--- End ---")

    print("\n" + "=" * 80)
    print(
        "Tip: 判定ロジックを変更するには src/clients/llm_client.py の check_spoiler を編集"
    )
    print("=" * 80)

    return 0


def cmd_interview(args):
    """interviewサブコマンド: インタビュー要約をテスト

    2つのモードをサポート:
    1. Groundingモード (推奨): --team と --opponent を指定
       例: python tune_gemini.py interview --team "Arsenal" --opponent "Bournemouth"
    2. Legacyモード: --articles-file を指定（旧式）
    """
    load_dotenv()

    # Groundingモード: --team と --opponent を使用
    if args.team and args.opponent:
        target_team = args.team
        opponent_team = args.opponent

        print_header(
            f"GEMINI INTERVIEW SUMMARY (Grounding) | {target_team} vs {opponent_team}"
        )
        print("Mode: Grounding (LLM will search for relevant information)")
        print(f"Target Team: {target_team}")
        print(f"Opponent Team: {opponent_team}")
        print("-" * 40)

        print("\nPrompt template (from settings/gemini_prompts.py):")
        print("  Task: Search and summarize manager press conference (1500-2000 chars)")
        print("  Constraints: No meta-intro, dynamic subheaders, opponent-focused")
        print("-" * 40)

        # 生成実行
        client = LLMClient(use_mock=args.mock)

        print("\n--- Generated Output ---")
        try:
            result = client.summarize_interview(
                team_name=target_team,
                articles=[],  # Groundingモードでは空
                opponent_team=opponent_team,
            )
            print(result)
            print(f"\n(Length: {len(result)} chars)")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback

            traceback.print_exc()
            return 1
        print("--- End ---")

        print("\n" + "=" * 80)
        print(
            "Tip: プロンプトを変更するには settings/gemini_prompts.py の interview を編集"
        )
        print("=" * 80)

        return 0

    # Legacyモード: --articles-file を使用
    if not args.articles_file:
        print("ERROR: Either --team/--opponent OR --articles-file is required")
        print("\nUsage:")
        print(
            "  Grounding mode: python tune_gemini.py interview --team 'Arsenal' --opponent 'Bournemouth'"
        )
        print(
            "  Legacy mode:    python tune_gemini.py interview --articles-file articles.json --home 'Arsenal'"
        )
        return 1

    # ファイルから記事を読み込む
    with open(args.articles_file, encoding="utf-8") as f:
        data = json.load(f)

    # インタビュー記事のみ抽出（tune_news_search.pyの出力形式に対応）
    target_team = args.home  # --home で指定されたチームを対象とする

    articles = [
        a
        for a in data
        if (
            a.get("type", "").startswith("interview_")
            and a.get("team", "").lower() == target_team.lower()
        )
    ]

    if not articles:
        print(f"ERROR: No interview articles found for team '{target_team}' in file")
        print(f"Debug: Found {len(data)} total articles.")
        for i, a in enumerate(data[:3]):
            print(f"  {i}: type={a.get('type')}, team={a.get('team')}")
        return 1

    print_header(f"GEMINI INTERVIEW SUMMARY (Legacy) | {target_team}")
    print(f"Input: {len(articles)} articles")

    print_articles_context(articles)

    print("\nPrompt template (from settings/gemini_prompts.py):")
    print("  Task: Summarize manager/player comments (1500-2000 chars)")
    print("-" * 40)

    # 生成実行
    client = LLMClient(use_mock=args.mock)

    print("\n--- Generated Output ---")
    try:
        result = client.summarize_interview(
            team_name=target_team,
            articles=articles,
            opponent_team=args.opponent,  # オプショナル
        )
        print(result)
        print(f"\n(Length: {len(result)} chars)")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    print("--- End ---")

    print("\n" + "=" * 80)
    print(
        "Tip: プロンプトを変更するには settings/gemini_prompts.py の interview を編集"
    )
    print("=" * 80)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Geminiプロンプトチューニングツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    # 共通引数
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument(
        "--home",
        default="Manchester City",
        help="ホームチーム (interviewでは対象チームとして使用)",
    )
    common_args.add_argument("--away", default="West Ham", help="アウェイチーム")
    common_args.add_argument("--mock", action="store_true", help="モックモードで実行")

    # summary サブコマンド
    summary_parser = subparsers.add_parser(
        "summary", parents=[common_args], help="ニュース要約をテスト"
    )
    summary_parser.add_argument("--articles-file", help="記事JSONファイル")

    # preview サブコマンド
    preview_parser = subparsers.add_parser(
        "preview", parents=[common_args], help="戦術プレビューをテスト"
    )
    preview_parser.add_argument("--articles-file", help="記事JSONファイル（必須）")
    preview_parser.add_argument(
        "--home-formation", help="ホームフォーメーション (例: 4-3-3)"
    )
    preview_parser.add_argument(
        "--away-formation", help="アウェイフォーメーション (例: 4-4-2)"
    )
    preview_parser.add_argument("--home-lineup", help="ホームスタメン (カンマ区切り)")
    preview_parser.add_argument("--away-lineup", help="アウェイスタメン (カンマ区切り)")
    preview_parser.add_argument(
        "--competition", help="大会名 (デフォルト: Premier League)"
    )

    # interview サブコマンド
    interview_parser = subparsers.add_parser(
        "interview", parents=[common_args], help="インタビュー要約をテスト"
    )
    interview_parser.add_argument(
        "--articles-file", help="記事JSONファイル（Legacyモード用）"
    )
    interview_parser.add_argument("--team", help="対象チーム（Groundingモード用）")
    interview_parser.add_argument(
        "--opponent", help="対戦相手チーム（Groundingモード用）"
    )

    # spoiler サブコマンド
    spoiler_parser = subparsers.add_parser(
        "spoiler", parents=[common_args], help="ネタバレチェックをテスト"
    )
    spoiler_parser.add_argument("--text", help="チェック対象テキスト")

    args = parser.parse_args()

    if args.command == "summary":
        return cmd_summary(args)
    elif args.command == "preview":
        return cmd_preview(args)
    elif args.command == "interview":
        return cmd_interview(args)
    elif args.command == "spoiler":
        return cmd_spoiler(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
