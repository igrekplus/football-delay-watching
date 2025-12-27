#!/usr/bin/env python3
"""
ローカルキャッシュをGCSにアップロードするスクリプト

使用方法:
    python scripts/upload_cache_to_gcs.py [--dry-run]
    
オプション:
    --dry-run: 実際にアップロードせず、計画を表示するだけ
"""

import os
import sys
import json
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import storage

CACHE_DIR = Path("api_cache")
GCS_BUCKET_NAME = os.getenv("GCS_CACHE_BUCKET", "football-delay-watching-cache")


def upload_cache_to_gcs(dry_run: bool = False):
    """ローカルキャッシュをGCSにアップロード"""
    
    if not CACHE_DIR.exists():
        print(f"Cache directory not found: {CACHE_DIR}")
        return
    
    print(f"=== Upload Local Cache to GCS ===")
    print(f"Source: {CACHE_DIR}")
    print(f"Destination: gs://{GCS_BUCKET_NAME}/")
    print(f"Mode: {'DRY RUN' if dry_run else 'UPLOAD'}")
    print("-" * 60)
    
    # GCSクライアント初期化
    if not dry_run:
        try:
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            print(f"Connected to GCS bucket: {GCS_BUCKET_NAME}")
        except Exception as e:
            print(f"Failed to connect to GCS: {e}")
            return
    
    # 新形式のファイルを検索（サブディレクトリ内のJSONファイル）
    uploaded = 0
    skipped = 0
    failed = 0
    
    for subdir in ["fixtures", "lineups", "players", "injuries", "statistics", "headtohead"]:
        subdir_path = CACHE_DIR / subdir
        if not subdir_path.exists():
            continue
        
        for filepath in subdir_path.rglob("*.json"):
            relative_path = filepath.relative_to(CACHE_DIR)
            gcs_path = str(relative_path)
            
            print(f"Uploading: {relative_path}")
            
            if dry_run:
                uploaded += 1
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                blob = bucket.blob(gcs_path)
                blob.upload_from_string(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    content_type='application/json'
                )
                print(f"  [OK] -> gs://{GCS_BUCKET_NAME}/{gcs_path}")
                uploaded += 1
                
            except Exception as e:
                print(f"  [ERROR] {e}")
                failed += 1
    
    print()
    print("-" * 60)
    print(f"Summary: {uploaded} uploaded, {skipped} skipped, {failed} failed")
    
    if dry_run:
        print()
        print("This was a dry run. Run without --dry-run to actually upload.")


def check_gcs_connection():
    """GCS接続テスト"""
    print("Testing GCS connection...")
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        
        # バケットの存在確認
        if bucket.exists():
            print(f"✅ Connected to bucket: {GCS_BUCKET_NAME}")
            
            # ファイル数をカウント
            blobs = list(bucket.list_blobs(max_results=100))
            print(f"   Files in bucket: {len(blobs)}+")
            return True
        else:
            print(f"❌ Bucket not found: {GCS_BUCKET_NAME}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload local cache to GCS")
    parser.add_argument("--dry-run", action="store_true", help="Show upload plan without executing")
    parser.add_argument("--check", action="store_true", help="Check GCS connection only")
    
    args = parser.parse_args()
    
    if args.check:
        check_gcs_connection()
    else:
        upload_cache_to_gcs(dry_run=args.dry_run)
