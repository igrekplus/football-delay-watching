#!/usr/bin/env python3
"""
同国対決プロンプトチューニングツール

選手間の関係性・小ネタ生成プロンプトを調整する。

Usage:
    # 日本人対決をテスト
    python scripts/tuning/tune_same_country.py \
        --home-team "Brighton" \
        --away-team "Arsenal" \
        --matchups '[{"country": "Japan", "home_players": ["三笘薫"], "away_players": ["冨安健洋"]}]'
    
    # 複数国籍をテスト
    python scripts/tuning/tune_same_country.py \
        --home-team "Liverpool" \
        --away-team "Chelsea" \
        --matchups '[{"country": "Japan", "home_players": ["遠藤航"], "away_players": ["守田英正"]}, {"country": "Portugal", "home_players": ["Diogo Jota"], "away_players": ["Enzo Fernandez"]}]'
"""

import argparse
import json
import os
import sys
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

from src.clients.llm_client import LLMClient


def print_header(title: str):
    """ヘッダーを表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_matchups(matchups: List[Dict]):
    """マッチアップ情報を表示"""
    print("📋 Input Matchups:")
    for m in matchups:
        print(f"  - {m['country']}: {m['home_players']} vs {m['away_players']}")
    print()


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="同国対決プロンプトチューニング")
    parser.add_argument("--home-team", required=True, help="ホームチーム名")
    parser.add_argument("--away-team", required=True, help="アウェイチーム名")
    parser.add_argument("--matchups", required=True, help="マッチアップJSON (例: '[{\"country\": \"Japan\", ...}]')")
    parser.add_argument("--mock", action="store_true", help="モックモードで実行")
    
    args = parser.parse_args()
    
    # JSONパース
    try:
        matchups = json.loads(args.matchups)
    except json.JSONDecodeError as e:
        print(f"❌ JSONパースエラー: {e}")
        return 1
    
    print_header("同国対決チューニング")
    print(f"🏟️  試合: {args.home_team} vs {args.away_team}")
    print_matchups(matchups)
    
    # LLMクライアント初期化
    client = LLMClient(use_mock=args.mock)
    
    if args.mock:
        print("⚠️  モックモードで実行中\n")
    
    # 生成実行
    print("🤖 Generating trivia...")
    print("-" * 40)
    
    result = client.generate_same_country_trivia(
        home_team=args.home_team,
        away_team=args.away_team,
        matchups=matchups
    )
    
    print("\n📝 Output:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    
    # 統計情報
    print(f"\n📊 Statistics:")
    print(f"  - 文字数: {len(result)}文字")
    print(f"  - 国籍数: {len(matchups)}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
