import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

from src.clients.cache_store import create_cache_store
from src.clients.youtube_client import YouTubeSearchClient


def verify_youtube_gcs_cache():
    print("Verifying YouTube GCS Cache Integration...")

    # CacheStore (GCS) の作成
    store = create_cache_store(backend="gcs")

    # YouTubeSearchClient の作成 (APIキー不要)
    client = YouTubeSearchClient(api_key="dummy_key", cache_store=store)

    # テストデータ
    test_query = "GCS Integration Test"
    test_results = [
        {"video_id": "test123", "title": "Test Video", "channel_name": "Test Channel"}
    ]

    # キャッシュパスの生成 (内部メソッドをテスト用に公開想定、または直接呼び出し)
    cache_path = client._get_cache_path(
        query=test_query, channel_id=None, published_after=None, published_before=None
    )

    print(f"Generated cache path: {cache_path}")

    # キャッシュ書き込み
    print("Writing to GCS...")
    client._write_cache(cache_path, test_results)

    # キャッシュ読み込み
    print("Reading from GCS...")
    cached_data = client._read_cache(cache_path)

    if (
        cached_data
        and len(cached_data) == 1
        and cached_data[0]["video_id"] == "test123"
    ):
        print("SUCCESS: GCS Cache write and read verified!")
        return True
    else:
        print(f"FAILURE: Data mismatch. Got: {cached_data}")
        return False


if __name__ == "__main__":
    if verify_youtube_gcs_cache():
        sys.exit(0)
    else:
        sys.exit(1)
