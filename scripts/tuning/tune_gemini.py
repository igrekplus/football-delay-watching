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
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

from src.clients.llm_client import LLMClient


def print_header(title: str):
    """ヘッダーを表示"""
    print("=" * 80)
    print(title)
    print("=" * 80)


def load_articles(path: str) -> List[Dict]:
    """記事JSONを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # リスト形式をそのまま返す
    if isinstance(data, list):
        return data
    
    # 他の形式の場合
    return data.get("articles", data.get("kept", []))


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
    print("  Task: Summarize news snippets into Japanese pre-match summary (600-1000 chars)")
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
    
    print("\n" + "=" * 80)
    print("⚠️  WARNING: 現在のプロンプトは「いない選手を含む妄想」を生成する問題あり")
    print("    プロンプトに「記事に記載された情報のみを使用せよ」を強制する必要がある")
    print("=" * 80)
    
    print("\nPrompt template (from llm_client.py):")
    print("  Task: Extract tactical analysis (Japanese)")
    print("  Constraints: Focus on formations/matchups, do NOT reveal results")
    print("-" * 40)
    
    # 生成実行
    client = LLMClient(use_mock=args.mock)
    
    print("\n--- Generated Output ---")
    try:
        result = client.generate_tactical_preview(
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
    print("Tip: プロンプトを変更するには src/clients/llm_client.py の generate_tactical_preview を編集")
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
    print("Tip: 判定ロジックを変更するには src/clients/llm_client.py の check_spoiler を編集")
    print("=" * 80)
    
    return 0


def cmd_interview(args):
    """interviewサブコマンド: インタビュー要約をテスト"""
    load_dotenv()
    
    if not args.articles_file:
        print("ERROR: --articles-file is required")
        return 1
    
    # ファイルから記事を読み込む
    with open(args.articles_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # インタビュー記事のみ抽出（tune_news_search.pyの出力形式に対応）
    # type="interview_manager" または type="interview_player"
    # かつ team が args.home (Sunderland等) と一致するもの
    target_team = args.home  # --home で指定されたチームを対象とする
    
    articles = [
        a for a in data 
        if (a.get("type", "").startswith("interview_") and 
            a.get("team", "").lower() == target_team.lower())
    ]
    
    if not articles:
        print(f"ERROR: No interview articles found for team '{target_team}' in file")
        # デバッグ用に全件表示
        print(f"Debug: Found {len(data)} total articles.")
        for i, a in enumerate(data[:3]):
            print(f"  {i}: type={a.get('type')}, team={a.get('team')}")
        return 1
    
    print_header(f"GEMINI INTERVIEW SUMMARY | {target_team}")
    print(f"Input: {len(articles)} articles")
    
    print_articles_context(articles)
    
    print("\nPrompt template (from llm_client.py):")
    print("  Task: Summarize manager/player comments (200-300 chars)")
    print("  Format: 【Team】...")
    print("-" * 40)
    
    # 生成実行
    client = LLMClient(use_mock=args.mock)
    
    print("\n--- Generated Output ---")
    try:
        result = client.summarize_interview(
            team_name=target_team,
            articles=articles,
        )
        print(result)
        print(f"\n(Length: {len(result)} chars)")
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    print("--- End ---")
    
    print("\n" + "=" * 80)
    print("Tip: プロンプトを変更するには src/clients/llm_client.py の summarize_interview を編集")
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
    common_args.add_argument("--home", default="Manchester City", help="ホームチーム (interviewでは対象チームとして使用)")
    common_args.add_argument("--away", default="West Ham", help="アウェイチーム")
    common_args.add_argument("--mock", action="store_true", help="モックモードで実行")
    
    # summary サブコマンド
    summary_parser = subparsers.add_parser("summary", parents=[common_args], help="ニュース要約をテスト")
    summary_parser.add_argument("--articles-file", help="記事JSONファイル")
    
    # preview サブコマンド
    preview_parser = subparsers.add_parser("preview", parents=[common_args], help="戦術プレビューをテスト")
    preview_parser.add_argument("--articles-file", help="記事JSONファイル")
    
    # interview サブコマンド
    interview_parser = subparsers.add_parser("interview", parents=[common_args], help="インタビュー要約をテスト")
    interview_parser.add_argument("--articles-file", help="記事JSONファイル")
    
    # spoiler サブコマンド
    spoiler_parser = subparsers.add_parser("spoiler", parents=[common_args], help="ネタバレチェックをテスト")
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
