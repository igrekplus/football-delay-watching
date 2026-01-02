#!/usr/bin/env python3
"""
YouTube検索チューニングツール

クエリやフィルタを調整しながら、検索結果の品質を確認する。
本番デバッグを回さずに高速に反復できる。

Usage:
    python scripts/tuning/tune_youtube.py query "Manchester City training"
    python scripts/tuning/tune_youtube.py category historic --home "Man City" --away "West Ham"
    python scripts/tuning/tune_youtube.py filter --input results.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
import pytz

from src.clients.youtube_client import YouTubeSearchClient
from src.youtube_filter import YouTubePostFilter
from settings.search_specs import (
    YOUTUBE_SEARCH_SPECS,
    build_youtube_query,
    get_youtube_time_window,
    get_youtube_exclude_filters,
)
from settings.channels import is_trusted_channel, get_channel_info


def print_header(title: str):
    """ヘッダーを表示"""
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_video(idx: int, video: Dict, status: str, reason: str = ""):
    """動画情報を表示"""
    channel = video.get("channel_name", "Unknown")
    is_trusted = is_trusted_channel(video.get("channel_id", ""))
    trusted_mark = "✓ trusted" if is_trusted else ""
    
    status_icon = "✅ KEPT" if status == "kept" else f"❌ REMOVED: {reason}"
    
    print(f"\n{idx}. [{status_icon}] {video.get('title', 'No Title')}")
    print(f"   Channel: {channel} ({trusted_mark})" if trusted_mark else f"   Channel: {channel}")
    print(f"   URL: {video.get('url', '')}")
    print(f"   Published: {video.get('published_at', '')[:10]}")


def print_summary(kept: int, removed: int, tip: str = ""):
    """サマリーを表示"""
    print("\n" + "=" * 80)
    print(f"SUMMARY: KEPT={kept} | REMOVED={removed}")
    if tip:
        print(f"Tip: {tip}")
    print("=" * 80)


def cmd_query(args):
    """queryサブコマンド: クエリを直接テスト"""
    load_dotenv()
    
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY or GOOGLE_API_KEY is not set")
        return 1
    
    client = YouTubeSearchClient(api_key=api_key, cache_enabled=True)
    filter_instance = YouTubePostFilter()
    
    # 時間ウィンドウ計算
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    published_after = now - timedelta(days=args.days_before)
    published_before = now
    
    print_header(f"QUERY: {args.query}")
    print(f"PARAMS: published_after={published_after.strftime('%Y-%m-%d')}, "
          f"published_before={published_before.strftime('%Y-%m-%d')}, "
          f"max_results={args.max_results}")
    print("=" * 80)
    
    # 検索実行
    videos = client.search(
        query=args.query,
        published_after=published_after.astimezone(pytz.UTC),
        published_before=published_before.astimezone(pytz.UTC),
        max_results=args.max_results,
    )
    
    if not videos:
        print("\nNo results found.")
        return 0
    
    print(f"\nRAW API RESULTS ({len(videos)} 件):")
    
    # フィルタ適用
    if args.no_filter:
        for idx, video in enumerate(videos, 1):
            print_video(idx, video, "kept")
        print_summary(len(videos), 0)
    else:
        # デフォルトの除外フィルタを適用
        exclude_filters = ["match_highlights", "highlights", "full_match", "live_stream", "reaction"]
        filter_result = filter_instance.apply_filters(videos, exclude_filters)
        
        kept = filter_result["kept"]
        removed = filter_result["removed"]
        
        # kept を表示
        for idx, video in enumerate(kept, 1):
            print_video(idx, video, "kept")
        
        # removed を表示
        for idx, video in enumerate(removed, len(kept) + 1):
            reason = video.get("filter_reason", "unknown")
            print_video(idx, video, "removed", reason)
        
        print_summary(
            len(kept), 
            len(removed),
            "フィルタを調整するには settings/search_specs.py の exclude_filters を編集"
        )
    
    print(f"\nAPI calls: {client.api_call_count} | Cache hits: {client.cache_hit_count}")
    return 0


def cmd_category(args):
    """categoryサブコマンド: カテゴリ別の自動クエリをテスト"""
    load_dotenv()
    
    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY or GOOGLE_API_KEY is not set")
        return 1
    
    category = args.category
    if category not in YOUTUBE_SEARCH_SPECS:
        print(f"ERROR: Unknown category '{category}'")
        print(f"Available: {', '.join(YOUTUBE_SEARCH_SPECS.keys())}")
        return 1
    
    # キックオフ時刻
    jst = pytz.timezone("Asia/Tokyo")
    if args.kickoff_jst:
        kickoff = datetime.strptime(args.kickoff_jst, "%Y-%m-%d %H:%M")
        kickoff = jst.localize(kickoff).astimezone(pytz.UTC)
    else:
        # デフォルト: 翌日00:00 JST
        tomorrow = datetime.now(jst).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        kickoff = tomorrow.astimezone(pytz.UTC)
    
    # クエリ生成用の変数
    query_vars = {}
    if args.home:
        query_vars["home_team"] = args.home
    if args.away:
        query_vars["away_team"] = args.away
    if args.team:
        query_vars["team_name"] = args.team
    if args.manager:
        query_vars["manager_name"] = args.manager
    if args.player:
        query_vars["player_name"] = args.player
    
    # カテゴリに応じた必須変数チェック
    if category == "historic" and (not args.home or not args.away):
        print("ERROR: --home and --away are required for 'historic' category")
        return 1
    if category in ["training", "tactical"] and not args.team:
        print(f"ERROR: --team is required for '{category}' category")
        return 1
    if category == "player_highlight" and not args.player:
        print("ERROR: --player is required for 'player_highlight' category")
        return 1
    if category == "press_conference" and not args.team:
        query_vars["team_name"] = args.home or args.away
        if not query_vars["team_name"]:
            print("ERROR: --team or --home/--away is required for 'press_conference' category")
            return 1
    
    # クエリ生成
    try:
        query = build_youtube_query(category, **query_vars)
    except KeyError as e:
        print(f"ERROR: Missing variable for query template: {e}")
        return 1
    
    # 時間ウィンドウ
    published_after, published_before = get_youtube_time_window(category, kickoff)
    
    print_header(f"CATEGORY: {category} ({YOUTUBE_SEARCH_SPECS[category]['label']})")
    print(f"QUERY: {query}")
    print(f"PARAMS: published_after={published_after.strftime('%Y-%m-%d')}, "
          f"published_before={published_before.strftime('%Y-%m-%d')}")
    print("=" * 80)
    
    # 検索実行
    client = YouTubeSearchClient(api_key=api_key, cache_enabled=True)
    filter_instance = YouTubePostFilter()
    
    videos = client.search(
        query=query,
        published_after=published_after,
        published_before=published_before,
        max_results=args.max_results,
    )
    
    if not videos:
        print("\nNo results found.")
        print("\nTip: クエリを変更するには settings/search_specs.py を編集")
        return 0
    
    print(f"\nRAW API RESULTS ({len(videos)} 件):")
    
    # フィルタ適用
    exclude_filters = get_youtube_exclude_filters(category)
    filter_result = filter_instance.apply_filters(videos, exclude_filters)
    
    kept = filter_result["kept"]
    removed = filter_result["removed"]
    
    # 信頼チャンネルでソート
    kept = filter_instance.sort_trusted(kept)
    
    for idx, video in enumerate(kept, 1):
        print_video(idx, video, "kept")
    
    if args.show_removed:
        for idx, video in enumerate(removed, len(kept) + 1):
            reason = video.get("filter_reason", "unknown")
            print_video(idx, video, "removed", reason)
    else:
        if removed:
            print(f"\n... {len(removed)} videos removed (use --show-removed to see)")
    
    print_summary(
        len(kept),
        len(removed),
        "クエリを変更するには settings/search_specs.py を編集"
    )
    
    print(f"\nAPI calls: {client.api_call_count} | Cache hits: {client.cache_hit_count}")
    
    # 結果保存
    if args.save:
        save_path = Path(args.save)
        save_data = {
            "category": category,
            "query": query,
            "kept": kept,
            "removed": removed,
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {save_path}")
    
    return 0


def cmd_filter(args):
    """filterサブコマンド: フィルタロジックをテスト"""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        return 1
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    videos = data if isinstance(data, list) else data.get("kept", []) + data.get("removed", [])
    
    if not videos:
        print("No videos in input file.")
        return 1
    
    print_header(f"FILTER TEST: {len(videos)} videos from {input_path.name}")
    
    filter_instance = YouTubePostFilter()
    
    # フィルタルール指定
    if args.exclude:
        exclude_filters = args.exclude
    else:
        exclude_filters = ["match_highlights", "highlights", "full_match", "live_stream", "reaction"]
    
    print(f"FILTERS: {', '.join(exclude_filters)}")
    print("=" * 80)
    
    filter_result = filter_instance.apply_filters(videos, exclude_filters)
    kept = filter_result["kept"]
    removed = filter_result["removed"]
    
    for idx, video in enumerate(kept, 1):
        print_video(idx, video, "kept")
    
    for idx, video in enumerate(removed, len(kept) + 1):
        reason = video.get("filter_reason", "unknown")
        print_video(idx, video, "removed", reason)
    
    print_summary(len(kept), len(removed))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="YouTube検索チューニングツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")
    
    # query サブコマンド
    query_parser = subparsers.add_parser("query", help="クエリを直接テスト")
    query_parser.add_argument("query", help="検索クエリ")
    query_parser.add_argument("--days-before", type=int, default=7, help="何日前から検索 (default: 7)")
    query_parser.add_argument("--max-results", type=int, default=20, help="表示件数 (default: 20)")
    query_parser.add_argument("--no-filter", action="store_true", help="フィルタを適用しない")
    
    # category サブコマンド
    cat_parser = subparsers.add_parser("category", help="カテゴリ別の自動クエリをテスト")
    cat_parser.add_argument("category", choices=list(YOUTUBE_SEARCH_SPECS.keys()), help="検索カテゴリ")
    cat_parser.add_argument("--home", help="ホームチーム")
    cat_parser.add_argument("--away", help="アウェイチーム")
    cat_parser.add_argument("--team", help="チーム名（単体検索用）")
    cat_parser.add_argument("--manager", help="監督名")
    cat_parser.add_argument("--player", help="選手名")
    cat_parser.add_argument("--kickoff-jst", help="キックオフJST (YYYY-MM-DD HH:MM)")
    cat_parser.add_argument("--max-results", type=int, default=20, help="表示件数 (default: 20)")
    cat_parser.add_argument("--show-removed", action="store_true", help="除外動画も表示")
    cat_parser.add_argument("--save", help="結果をJSONに保存")
    
    # filter サブコマンド
    filter_parser = subparsers.add_parser("filter", help="フィルタロジックをテスト")
    filter_parser.add_argument("--input", required=True, help="入力JSONファイル")
    filter_parser.add_argument("--exclude", nargs="+", help="適用する除外フィルタ")
    
    args = parser.parse_args()
    
    if args.command == "query":
        return cmd_query(args)
    elif args.command == "category":
        return cmd_category(args)
    elif args.command == "filter":
        return cmd_filter(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
