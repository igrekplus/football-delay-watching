#!/usr/bin/env python3
"""
API-Football ヘルスチェック・クォータ確認ツール

使用方法:
    python scripts/check_api_status.py
    
    # または実行権限を付与して
    chmod +x scripts/check_api_status.py
    ./scripts/check_api_status.py
"""

import os
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests


def check_api_football():
    """API-Footballのステータスとクォータを確認"""
    load_dotenv()
    
    api_key = os.getenv('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY が設定されていません")
        return False
    
    print("=" * 50)
    print("📊 API-Football ステータス確認")
    print("=" * 50)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # タイムゾーン情報を取得（軽量なエンドポイント）
        resp = requests.get(
            'https://v3.football.api-sports.io/timezone',
            headers={
                'x-apisports-key': api_key
            },
            timeout=10
        )
        
        # クォータ情報
        quota_remaining = resp.headers.get('x-ratelimit-requests-remaining', 'N/A')
        quota_limit = resp.headers.get('x-ratelimit-requests-limit', 'N/A')
        
        # /tmp/quota.txt に書き込み
        quota_file = "/tmp/quota.txt"
        with open(quota_file, "w", encoding="utf-8") as f:
            f.write(f"API-Football: Remaining: {quota_remaining} / Limit: {quota_limit}\n")
        
        print(f"📡 ステータスコード: {resp.status_code}")
        print(f"📈 クォータ: {quota_remaining} / {quota_limit}")
        print(f"📝 クォータ情報を {quota_file} に保存しました")
        print()
        
        if resp.status_code == 200:
            print("✅ API-Football: 正常")
            return True
        elif resp.status_code == 429:
            print("⛔ API-Football: クォータ超過 (429 Too Many Requests)")
            print("   → UTCの00:00 (JST 09:00) にリセットされます")
            return False
        elif resp.status_code == 401:
            print("❌ API-Football: 認証エラー (APIキーが無効)")
            return False
        else:
            print(f"⚠️ API-Football: 予期しないステータス ({resp.status_code})")
            print(f"   レスポンス: {resp.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ API-Football: タイムアウト (10秒)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ API-Football: 接続エラー ({e})")
        return False
    except Exception as e:
        print(f"❌ API-Football: エラー ({e})")
        return False


if __name__ == "__main__":
    success = check_api_football()
    print()
    print("=" * 50)
    sys.exit(0 if success else 1)
