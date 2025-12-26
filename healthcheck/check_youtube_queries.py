#!/usr/bin/env python3
"""
YouTube Data API query tuning helper for a specific match.

- Focus: Manchester City vs West Ham (defaults)
- Scope: training + player highlight queries only
- Uses YouTube Data API search.list
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from settings.channels import TRUSTED_CHANNELS
from src.youtube_service import YouTubeService

# Defaults for this session
DEFAULT_HOME_TEAM = "Manchester City"
DEFAULT_AWAY_TEAM = "West Ham"
DEFAULT_KICKOFF_JST = "2025-12-21 00:00"  # adjust as needed
DEFAULT_PLAYERS = [
    "Erling Haaland",
    "Phil Foden",
    "Jarrod Bowen",
]

# Known official channel IDs (add more as needed)
TEAM_CHANNEL_IDS = {
    "Manchester City": "UCkzCjdRMrW2vXLx8mvPVLdQ",
    # "West Ham": "...",  # unknown
}

# Keyword flags (do not hard-exclude; just flag)
TRAINING_FLAG_KEYWORDS = [
    "highlight",
    "highlights",
    "goal",
    "goals",
    "match",
    "vs",
    "full match",
    "extended",
]
PLAYER_FLAG_KEYWORDS = [
    "full match",
    "match highlights",
    "extended highlights",
]


def _find_channel_id_by_name(team_name: str) -> Optional[str]:
    if team_name in TEAM_CHANNEL_IDS:
        return TEAM_CHANNEL_IDS[team_name]
    # Fallback: try matching trusted channel display names
    lower = team_name.lower()
    for cid, info in TRUSTED_CHANNELS.items():
        if info.get("name", "").lower() == lower:
            return cid
    return None


def _parse_kickoff_jst(kickoff_jst: str) -> datetime:
    # JST -> UTC
    import pytz

    jst = pytz.timezone("Asia/Tokyo")
    dt = datetime.strptime(kickoff_jst, "%Y-%m-%d %H:%M")
    return jst.localize(dt).astimezone(pytz.UTC)


def _search_videos(
    yt: YouTubeService,
    query: str,
    published_after: Optional[datetime],
    published_before: Optional[datetime],
    max_results: int,
    relevance_language: Optional[str],
    region_code: Optional[str],
    channel_id: Optional[str],
) -> List[Dict]:
    results = yt.search_videos_raw(
        query=query,
        published_after=published_after,
        published_before=published_before,
        max_results=max_results,
        relevance_language=relevance_language,
        region_code=region_code,
        channel_id=channel_id,
    )

    return results


def _flag_keywords(text: str, keywords: List[str]) -> List[str]:
    lowered = text.lower()
    return [kw for kw in keywords if kw in lowered]


def _print_results(label: str, results: List[Dict], flag_keywords: List[str]):
    print("=" * 80)
    print(f"{label} ({len(results)} results)")
    print("=" * 80)
    for r in results:
        flags = _flag_keywords(f"{r['title']} {r['description']}", flag_keywords)
        flag_str = f" [FLAG: {', '.join(flags)}]" if flags else ""
        channel_title = r.get("channel_title") or r.get("channel_name") or "Unknown"
        print(f"- {r['title']}{flag_str}")
        print(f"  {channel_title} | {r['published_at']}")
        print(f"  {r['url']}")
    print()



def _run_training_queries(
    yt: YouTubeService,
    team: str,
    kickoff_utc: datetime,
    max_results: int,
    window_hours: int,
    prefer_official: bool,
    min_official_results: int,
):
    published_after = kickoff_utc - timedelta(hours=window_hours)
    published_before = kickoff_utc

    channel_id = _find_channel_id_by_name(team) if prefer_official else None

    queries = [
        f"{team} training",
        f"{team} training session",
        f"{team} pre match training",
        f"{team} open training",
    ]

    for q in queries:
        if channel_id:
            try:
                results = _search_videos(
                    yt,
                    q,
                    published_after,
                    published_before,
                    max_results,
                    "en",
                    None,
                    channel_id,
                )
                results = yt.apply_trusted_channel_sort(results)
                label = f"TRAINING (official only) | {team} | query: {q}"
                _print_results(label, results, TRAINING_FLAG_KEYWORDS)
                if len(results) < min_official_results:
                    fallback = _search_videos(
                        yt,
                        q,
                        published_after,
                        published_before,
                        max_results,
                        "en",
                        None,
                        None,
                    )
                    fallback = yt.apply_trusted_channel_sort(fallback)
                    label = f"TRAINING (fallback) | {team} | query: {q}"
                    _print_results(label, fallback, TRAINING_FLAG_KEYWORDS)
            except Exception as e:
                print(f"[ERROR] {team} | query: {q} | {e}")
        else:
            try:
                results = _search_videos(
                    yt,
                    q,
                    published_after,
                    published_before,
                    max_results,
                    "en",
                    None,
                    None,
                )
                results = yt.apply_trusted_channel_sort(results)
                label = f"TRAINING | {team} | query: {q}"
                _print_results(label, results, TRAINING_FLAG_KEYWORDS)
            except Exception as e:
                print(f"[ERROR] {team} | query: {q} | {e}")


def _run_player_queries(
    yt: YouTubeService,
    player: str,
    kickoff_utc: datetime,
    max_results: int,
    window_days: int,
    query_template: Optional[str] = None,
    show_filter: bool = True,
    relevance_language: Optional[str] = None,
    region_code: Optional[str] = None,
):
    published_after = kickoff_utc - timedelta(days=window_days)
    published_before = kickoff_utc

    if query_template:
        queries = [query_template.format(player=player)]
    else:
        queries = [
            f"{player} goals",
            f"{player} best goals",
            f"{player} skills",
            f"{player} highlights",
            f"{player} play",
        ]

    for q in queries:
        try:
            results = _search_videos(
                yt,
                q,
                published_after,
                published_before,
                max_results,
                relevance_language,
                region_code,
                None,
            )
            results = yt.apply_trusted_channel_sort(results)
            raw_label = f"PLAYER RAW | {player} | query: {q}"
            _print_results(raw_label, results, PLAYER_FLAG_KEYWORDS)

            if show_filter:
                filtered = yt.apply_player_post_filter(results)
                filtered["kept"] = yt.apply_trusted_channel_sort(filtered["kept"])
                kept_label = f"PLAYER FILTERED (KEPT) | {player} | query: {q}"
                _print_results(kept_label, filtered["kept"], PLAYER_FLAG_KEYWORDS)

                removed = filtered["removed"]
                print("=" * 80)
                print(f"PLAYER FILTERED (REMOVED) | {player} | query: {q} ({len(removed)} removed)")
                print("=" * 80)
                for r in removed:
                    reason = r.get("filter_reason", "unknown")
                    channel_title = r.get("channel_title") or r.get("channel_name") or "Unknown"
                    print(f"- {r['title']} [REMOVED: {reason}]")
                    print(f"  {channel_title} | {r['published_at']}")
                    print(f"  {r['url']}")
                print()
        except Exception as e:
            print(f"[ERROR] {player} | query: {q} | {e}")


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--home", default=DEFAULT_HOME_TEAM)
    parser.add_argument("--away", default=DEFAULT_AWAY_TEAM)
    parser.add_argument("--kickoff-jst", default=DEFAULT_KICKOFF_JST)
    parser.add_argument("--players", nargs="*", default=DEFAULT_PLAYERS)
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--training-window-hours", type=int, default=72)
    parser.add_argument("--player-window-days", type=int, default=180)
    parser.add_argument("--player-query-template", default=None)
    parser.add_argument("--player-relevance-language", default=None)
    parser.add_argument("--player-region-code", default=None)
    parser.add_argument("--no-player-postfilter", dest="player_postfilter", action="store_false")
    parser.set_defaults(player_postfilter=True)
    parser.add_argument("--prefer-official", dest="prefer_official", action="store_true")
    parser.add_argument("--no-prefer-official", dest="prefer_official", action="store_false")
    parser.set_defaults(prefer_official=True)
    parser.add_argument("--min-official-results", type=int, default=2)
    parser.add_argument("--mode", choices=["training", "player", "all"], default="all")
    args = parser.parse_args()

    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("YOUTUBE_API_KEY or GOOGLE_API_KEY is not set")
        return 1

    kickoff_utc = _parse_kickoff_jst(args.kickoff_jst)

    print("=" * 80)
    print("YouTube query tuning session")
    print(f"Match: {args.home} vs {args.away}")
    print(f"Kickoff (JST): {args.kickoff_jst}")
    print(f"Kickoff (UTC): {kickoff_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max results per query: {args.max_results}")
    print("=" * 80)
    print()

    yt = YouTubeService(api_key=api_key)

    if args.mode in ("training", "all"):
        _run_training_queries(
            yt,
            args.home,
            kickoff_utc,
            args.max_results,
            args.training_window_hours,
            args.prefer_official,
            args.min_official_results,
        )
        _run_training_queries(
            yt,
            args.away,
            kickoff_utc,
            args.max_results,
            args.training_window_hours,
            args.prefer_official,
            args.min_official_results,
        )

    if args.mode in ("player", "all"):
        for p in args.players:
            _run_player_queries(
                yt,
                p,
                kickoff_utc,
                args.max_results,
                args.player_window_days,
                query_template=args.player_query_template,
                show_filter=args.player_postfilter,
                relevance_language=args.player_relevance_language,
                region_code=args.player_region_code,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
