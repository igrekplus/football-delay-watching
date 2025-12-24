#!/usr/bin/env python3
"""
YouTube Data API ヘルスチェック（最小クォータ版）

消費クォータ: 100ユニット（search.list 1回のみ）

使用方法:
    python healthcheck/check_youtube.py
"""

import os
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests


def _extract_error_reason(resp: requests.Response) -> Optional[str]:
    try:
        data = resp.json()
        errors = data.get("error", {}).get("errors", [])
        if errors:
            return errors[0].get("reason")
    except Exception:
        return None
    return None


def check_youtube_quota(api_key: str) -> bool:
    """
    YouTube Data API の疎通とクォータ状態を確認
    
    消費: 100ユニット（search.list 1回）
    """
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": api_key,
                "q": "test",  # 最小限のクエリ
                "part": "snippet",
                "type": "video",
                "maxResults": 1,
            },
            timeout=10,
        )
    except requests.exceptions.Timeout:
        print("❌ YouTube API: タイムアウト (10秒)")
        return False
    except Exception as e:
        print(f"❌ YouTube API: エラー ({e})")
        return False

    print(f"📡 ステータスコード: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        total = data.get("pageInfo", {}).get("totalResults", "N/A")
        print(f"📈 検索結果: {total} 件")
        print("✅ YouTube API: 正常")
        print("   消費: 100ユニット (search.list 1回)")
        print("   ⚠️ 残クォータはCloud Consoleで確認: https://console.cloud.google.com/apis/dashboard")
        return True

    if resp.status_code == 403:
        reason = _extract_error_reason(resp)
        if reason in {"quotaExceeded", "dailyLimitExceeded"}:
            print("⛔ YouTube API: クォータ超過")
            print("   → リセット時刻: 17:00 JST (太平洋時間 0:00)")
        else:
            print(f"❌ YouTube API: 認証エラー (reason: {reason})")
        return False

    print(f"⚠️ YouTube API: 予期しないステータス ({resp.status_code})")
    print(f"   レスポンス: {resp.text[:200]}")
    return False


def check_youtube():
    load_dotenv()

    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")

    print("=" * 50)
    print("📊 YouTube Data API ヘルスチェック（最小クォータ版）")
    print("=" * 50)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not api_key:
        print("❌ YOUTUBE_API_KEY / GOOGLE_API_KEY が設定されていません")
        return False

    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print()

    quota_ok = check_youtube_quota(api_key)

    return quota_ok


if __name__ == "__main__":
    success = check_youtube()
    print()
    print("=" * 50)
    sys.exit(0 if success else 1)
