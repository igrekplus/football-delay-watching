#!/usr/bin/env python3
"""
ニュース検索チューニングツール

Google Custom Search APIのクエリを調整しながら、検索結果の品質を確認する。

Usage:
    python scripts/tuning/tune_news_search.py query '"Manchester City" "West Ham" preview'
    python scripts/tuning/tune_news_search.py match --home "Man City" --away "West Ham" --save articles.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

from src.clients.google_search_client import GoogleSearchClient
from settings.search_specs import (
    GOOGLE_SEARCH_SPECS,
    build_google_query,
    get_google_search_params,
)


def print_header(title: str):
    """ヘッダーを表示"""
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_article(idx: int, article: Dict):
    """記事情報を表示"""
    relevance = article.get("relevance_score", 0)
    title = article.get("title", "No Title")
    source = article.get("source", article.get("displayLink", "Unknown"))
    url = article.get("url", article.get("link", ""))
    snippet = article.get("snippet", article.get("content", ""))[:200]
    
    print(f"\n{idx}. [relevance={relevance}] {title}")
    print(f"   Source: {source}")
    print(f"   URL: {url}")
    print(f"   Snippet: {snippet}...")


def cmd_query(args):
    """queryサブコマンド: クエリを直接テスト"""
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key or not engine_id:
        print("ERROR: GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set")
        return 1
    
    client = GoogleSearchClient(api_key=api_key, engine_id=engine_id, use_mock=False)
    
    print_header(f"QUERY: {args.query}")
    print(f"PARAMS: dateRestrict={args.date_restrict}, gl={args.gl}, num={args.num}")
    print("=" * 80)
    
    # 検索実行
    items = client.search(
        query=args.query,
        num=args.num,
        date_restrict=args.date_restrict,
        gl=args.gl,
    )
    
    if not items:
        print("\nNo results found.")
        print("\nTip: クエリを変更するか、--date-restrict を広げてみてください")
        return 0
    
    print(f"\nRESULTS ({len(items)} 件):")
    
    for idx, item in enumerate(items, 1):
        # relevance_score は両チーム名の有無で計算
        content_lower = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        relevance = 0
        if args.home and args.home.lower() in content_lower:
            relevance += 1
        if args.away and args.away.lower() in content_lower:
            relevance += 1
        item["relevance_score"] = relevance
        print_article(idx, item)
    
    print("\n" + "=" * 80)
    print("Tip: クエリを変更するには settings/search_specs.py の GOOGLE_SEARCH_SPECS を編集")
    print("=" * 80)
    
    # 結果保存
    if args.save:
        save_path = Path(args.save)
        articles = []
        for item in items:
            articles.append({
                "content": f"{item.get('title', '')}\n{item.get('snippet', '')}",
                "title": item.get("title", ""),
                "source": item.get("displayLink", "Unknown"),
                "url": item.get("link", ""),
                "relevance_score": item.get("relevance_score", 0),
            })
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {save_path}")
    
    return 0


def cmd_match(args):
    """matchサブコマンド: 試合指定で自動クエリをテスト"""
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key or not engine_id:
        print("ERROR: GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set")
        return 1
    
    client = GoogleSearchClient(api_key=api_key, engine_id=engine_id, use_mock=False)
    
    all_articles = []
    
    # 1. ニュース検索
    print_header(f"NEWS SEARCH: {args.home} vs {args.away}")
    
    news_query = build_google_query("news", home_team=args.home, away_team=args.away)
    news_params = get_google_search_params("news")
    
    print(f"QUERY: {news_query}")
    print(f"PARAMS: dateRestrict={news_params['date_restrict']}, gl={news_params['gl']}, num={news_params['num']}")
    print("=" * 80)
    
    news_items = client.search(
        query=news_query,
        num=news_params["num"],
        date_restrict=news_params["date_restrict"],
        gl=news_params["gl"],
    )
    
    if news_items:
        print(f"\nNEWS RESULTS ({len(news_items)} 件):")
        for idx, item in enumerate(news_items, 1):
            content_lower = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
            relevance = 0
            if args.home.lower() in content_lower:
                relevance += 1
            if args.away.lower() in content_lower:
                relevance += 1
            item["relevance_score"] = relevance
            print_article(idx, item)
            
            all_articles.append({
                "content": f"{item.get('title', '')}\n{item.get('snippet', '')}",
                "title": item.get("title", ""),
                "source": item.get("displayLink", "Unknown"),
                "url": item.get("link", ""),
                "relevance_score": relevance,
                "type": "news",
            })
    else:
        print("\nNo news results found.")
    
    # 2. インタビュー検索（両チーム）
    if not args.no_interview:
        for team in [args.home, args.away]:
            print("\n" + "-" * 80)
            print(f"INTERVIEW SEARCH: {team}")
            print("-" * 80)
            
            for search_type in ["interview_manager", "interview_player"]:
                query = build_google_query(search_type, team_name=team)
                params = get_google_search_params(search_type)
                
                items = client.search(
                    query=query,
                    num=params["num"],
                    date_restrict=params["date_restrict"],
                    gl=params["gl"],
                )
                
                label = "Manager" if "manager" in search_type else "Player"
                if items:
                    print(f"\n{label} ({len(items)} 件):")
                    for idx, item in enumerate(items, 1):
                        print(f"  {idx}. {item.get('title', '')[:60]}...")
                        all_articles.append({
                            "content": f"{item.get('title', '')}\n{item.get('snippet', '')}",
                            "title": item.get("title", ""),
                            "source": item.get("displayLink", "Unknown"),
                            "url": item.get("link", ""),
                            "type": search_type,
                            "team": team,
                        })
                else:
                    print(f"\n{label}: No results")
    
    print("\n" + "=" * 80)
    print(f"TOTAL: {len(all_articles)} articles")
    print("Tip: クエリを変更するには settings/search_specs.py を編集")
    print("=" * 80)
    
    # 結果保存
    if args.save:
        save_path = Path(args.save)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to: {save_path}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="ニュース検索チューニングツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")
    
    # query サブコマンド
    query_parser = subparsers.add_parser("query", help="クエリを直接テスト")
    query_parser.add_argument("query", help="検索クエリ")
    query_parser.add_argument("--date-restrict", default="d2", help="日付制限 (default: d2)")
    query_parser.add_argument("--gl", default="us", help="地域コード (default: us)")
    query_parser.add_argument("--num", type=int, default=10, help="取得件数 (default: 10)")
    query_parser.add_argument("--home", help="ホームチーム（relevance計算用）")
    query_parser.add_argument("--away", help="アウェイチーム（relevance計算用）")
    query_parser.add_argument("--save", help="結果をJSONに保存")
    
    # match サブコマンド
    match_parser = subparsers.add_parser("match", help="試合指定で自動クエリをテスト")
    match_parser.add_argument("--home", required=True, help="ホームチーム")
    match_parser.add_argument("--away", required=True, help="アウェイチーム")
    match_parser.add_argument("--no-interview", action="store_true", help="インタビュー検索をスキップ")
    match_parser.add_argument("--save", help="結果をJSONに保存")
    
    args = parser.parse_args()
    
    if args.command == "query":
        return cmd_query(args)
    elif args.command == "match":
        return cmd_match(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
