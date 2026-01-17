#!/usr/bin/env python3
"""
Issue #107 テスト: search_override統計確認
"""

import sys

sys.path.insert(0, "/Users/nagataryou/football-delay-watching")

# ロギング設定
import logging
from datetime import datetime, timedelta

import pytz

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from src.youtube_service import YouTubeService


def mock_search(params):
    """モック検索関数"""
    return [
        {
            "video_id": f"mock_{params['query'][:10]}",
            "title": f"Mock Video: {params['query']}",
            "url": "https://www.youtube.com/watch?v=mock123",
            "channel_id": "UC_mock",
            "channel_name": "Mock Channel",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "published_at": "2024-01-01T00:00:00Z",
            "description": "Mock description",
            "original_index": 0,
        }
    ]


def test_override_stats():
    """search_override使用時の統計確認"""
    print("=" * 60)
    print("Test: search_override統計テスト (Issue #107)")
    print("=" * 60)

    # search_overrideを設定したServiceを作成
    service = YouTubeService(search_override=mock_search)

    # 初期状態確認
    print("\n[初期状態]")
    print(f"  api_call_count: {service.api_call_count}")
    print(f"  cache_hit_count: {service.cache_hit_count}")
    print(f"  override_call_count: {service.override_call_count}")

    assert service.override_call_count == 0, "初期値は0であるべき"

    # 検索実行（1回目）
    print("\n[検索実行: 1回目]")
    datetime.now(pytz.UTC) + timedelta(hours=3)
    result1 = service._search_videos("test query 1", max_results=5)
    print(f"  結果: {len(result1)} 件")
    print(f"  override_call_count: {service.override_call_count}")

    assert service.override_call_count == 1, "1回目の呼び出し後は1であるべき"

    # 検索実行（2回目）
    print("\n[検索実行: 2回目]")
    result2 = service._search_videos("test query 2", max_results=5)
    print(f"  結果: {len(result2)} 件")
    print(f"  override_call_count: {service.override_call_count}")

    assert service.override_call_count == 2, "2回目の呼び出し後は2であるべき"

    # 最終確認
    print("\n[最終状態]")
    print(f"  api_call_count: {service.api_call_count} (変更なし)")
    print(f"  cache_hit_count: {service.cache_hit_count} (変更なし)")
    print(f"  override_call_count: {service.override_call_count}")

    print("\n" + "=" * 60)
    print("✅ テスト成功: search_override統計が正しく更新されています")
    print("=" * 60)


if __name__ == "__main__":
    test_override_stats()
