#!/usr/bin/env python3
"""
Google Custom Search API ヘルスチェック

使用方法:
    python healthcheck/check_google_search.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests


def check_google_search():
    """Google Custom Search APIのステータスを確認"""
    load_dotenv()
    
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    print("=" * 50)
    print("📊 Google Custom Search API ステータス確認")
    print("=" * 50)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not api_key:
        print("❌ GOOGLE_SEARCH_API_KEY が設定されていません")
        return False
        
    if not search_engine_id:
        print("❌ GOOGLE_SEARCH_ENGINE_ID が設定されていません")
        return False
    
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"🔍 Engine ID: {search_engine_id}")
    print()
    
    try:
        # テスト検索を実行
        resp = requests.get(
            'https://www.googleapis.com/customsearch/v1',
            params={
                'key': api_key,
                'cx': search_engine_id,
                'q': 'Premier League',
                'num': 1
            },
            timeout=10
        )
        
        print(f"📡 ステータスコード: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            total_results = data.get('searchInformation', {}).get('totalResults', 'N/A')
            print(f"📈 検索結果: {total_results} 件")
            print()
            print("✅ Google Custom Search API: 正常")
            print("   ⚠️ クォータ: 100クエリ/日 (Cloud Consoleで確認)")
            return True
        elif resp.status_code == 403:
            error = resp.json().get('error', {})
            message = error.get('message', 'Unknown error')
            print(f"❌ Google Custom Search API: 認証エラー")
            print(f"   → {message}")
            return False
        elif resp.status_code == 429:
            print("⛔ Google Custom Search API: クォータ超過")
            print("   → 100クエリ/日を超過しました。明日まで待つか有料プランに変更してください。")
            return False
        else:
            print(f"⚠️ Google Custom Search API: 予期しないステータス")
            print(f"   レスポンス: {resp.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Google Custom Search API: タイムアウト (10秒)")
        return False
    except Exception as e:
        print(f"❌ Google Custom Search API: エラー ({e})")
        return False


if __name__ == "__main__":
    success = check_google_search()
    print()
    print("=" * 50)
    sys.exit(0 if success else 1)
