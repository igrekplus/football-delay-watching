#!/usr/bin/env python3
"""
YouTube Data API query tuning helper.

本体の YouTubeService メソッドを直接使用してクエリをテスト・チューニングする。
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytz
from dotenv import load_dotenv

from src.youtube_service import YouTubeService

# デフォルト設定
DEFAULT_HOME_TEAM = "Manchester City"
DEFAULT_AWAY_TEAM = "West Ham"
DEFAULT_KICKOFF_JST = "2025-12-21 00:00"
DEFAULT_PLAYERS = ["Erling Haaland", "Phil Foden", "Jarrod Bowen"]

# 結果表示用のフラグキーワード
TRAINING_FLAG_KEYWORDS = ["highlight", "goal", "match", "vs", "extended"]
PLAYER_FLAG_KEYWORDS = ["full match", "match highlights", "extended highlights"]


def parse_kickoff_jst(kickoff_jst: str) -> datetime:
    """JST文字列をUTC datetimeに変換"""
    jst = pytz.timezone("Asia/Tokyo")
    dt = datetime.strptime(kickoff_jst, "%Y-%m-%d %H:%M")
    return jst.localize(dt).astimezone(pytz.UTC)


def flag_keywords(text: str, keywords: list[str]) -> list[str]:
    """テキストに含まれるキーワードをフラグとして返す"""
    lowered = text.lower()
    return [kw for kw in keywords if kw in lowered]


def print_results(label: str, results: list[dict], keywords: list[str]):
    """検索結果を整形して表示"""
    print("=" * 80)
    print(f"{label} ({len(results)} results)")
    print("=" * 80)
    for r in results:
        flags = flag_keywords(
            f"{r.get('title', '')} {r.get('description', '')}", keywords
        )
        flag_str = f" [FLAG: {', '.join(flags)}]" if flags else ""
        channel = r.get("channel_display") or r.get("channel_name", "Unknown")
        trusted = "✅" if r.get("is_trusted") else "⚠️"
        print(f"- {r.get('title', 'No Title')}{flag_str}")
        print(f"  {trusted} {channel} | {r.get('published_at', '')[:10]}")
        print(f"  {r.get('url', '')}")
    print()


def print_removed(label: str, removed: list[dict]):
    """除外された動画を表示"""
    print("=" * 80)
    print(f"{label} ({len(removed)} removed)")
    print("=" * 80)
    for r in removed:
        reason = r.get("filter_reason", "unknown")
        channel = r.get("channel_display") or r.get("channel_name", "Unknown")
        print(f"- {r.get('title', 'No Title')} [REMOVED: {reason}]")
        print(f"  {channel}")
    print()


def run_training_queries(
    yt: YouTubeService, teams: list[str], kickoff_utc: datetime, max_results: int
):
    """練習動画クエリをテスト"""
    print("\n" + "=" * 80)
    print("TRAINING QUERIES")
    print("=" * 80 + "\n")

    for team in teams:
        results = yt.search_training_videos(team, kickoff_utc, max_results)
        print_results(f"TRAINING | {team}", results, TRAINING_FLAG_KEYWORDS)


def run_player_queries(
    yt: YouTubeService,
    players: list[str],
    team: str,
    kickoff_utc: datetime,
    max_results: int,
    show_filter: bool,
):
    """選手紹介クエリをテスト"""
    print("\n" + "=" * 80)
    print("PLAYER QUERIES")
    print("=" * 80 + "\n")

    for player in players:
        result = yt.search_player_videos(
            player_name=player,
            team_name=team,
            kickoff_time=kickoff_utc,
            max_results=max_results,
            apply_post_filter=show_filter,
        )

        print_results(
            f"PLAYER | {player} ({team})", result["kept"], PLAYER_FLAG_KEYWORDS
        )

        if show_filter and result["removed"]:
            print_removed(f"PLAYER FILTERED OUT | {player}", result["removed"])


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="YouTube query tuning helper")
    parser.add_argument("--home", default=DEFAULT_HOME_TEAM, help="Home team name")
    parser.add_argument("--away", default=DEFAULT_AWAY_TEAM, help="Away team name")
    parser.add_argument(
        "--kickoff-jst",
        default=DEFAULT_KICKOFF_JST,
        help="Kickoff time in JST (YYYY-MM-DD HH:MM)",
    )
    parser.add_argument(
        "--players", nargs="*", default=DEFAULT_PLAYERS, help="Player names to search"
    )
    parser.add_argument(
        "--max-results", type=int, default=5, help="Max results per query"
    )
    parser.add_argument(
        "--no-filter",
        dest="filter",
        action="store_false",
        help="Disable player post-filter",
    )
    parser.set_defaults(filter=True)
    parser.add_argument(
        "--mode",
        choices=["training", "player", "all"],
        default="all",
        help="Query mode",
    )
    args = parser.parse_args()

    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY or GOOGLE_API_KEY is not set")
        return 1

    kickoff_utc = parse_kickoff_jst(args.kickoff_jst)

    print("=" * 80)
    print("YouTube Query Tuning Session")
    print(f"Match: {args.home} vs {args.away}")
    print(f"Kickoff (JST): {args.kickoff_jst}")
    print(f"Kickoff (UTC): {kickoff_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max results: {args.max_results}")
    print(f"Post-filter: {'ON' if args.filter else 'OFF'}")
    print("=" * 80)

    yt = YouTubeService(api_key=api_key, cache_enabled=True)

    if args.mode in ("training", "all"):
        run_training_queries(yt, [args.home, args.away], kickoff_utc, args.max_results)

    if args.mode in ("player", "all"):
        # ホームチームの選手として検索（チーム名を含めることで精度向上）
        run_player_queries(
            yt, args.players, args.home, kickoff_utc, args.max_results, args.filter
        )

    print("\n" + "=" * 80)
    print(f"API calls: {yt.api_call_count} | Cache hits: {yt.cache_hit_count}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
