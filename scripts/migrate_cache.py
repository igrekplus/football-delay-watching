#!/usr/bin/env python3
"""
キャッシュ移行スクリプト

旧形式（ハッシュベース）のキャッシュファイルを新形式（可読ファイル名）に変換する。
変換後のファイルには _cached_at メタデータが付与される。

使用方法:
    python scripts/migrate_cache.py [--dry-run]
    
オプション:
    --dry-run: 実際にファイルを移動せず、移行計画を表示するだけ
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

CACHE_DIR = Path("api_cache")


def parse_legacy_cache_file(filepath: Path) -> dict:
    """旧形式のキャッシュファイルからメタデータを抽出"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # API-Footballのレスポンス形式を解析
        endpoint = data.get("get", "")
        params = data.get("parameters", {})
        
        return {
            "endpoint": endpoint,
            "params": params,
            "data": data,
            "file_mtime": datetime.fromtimestamp(filepath.stat().st_mtime)
        }
    except Exception as e:
        print(f"  [ERROR] Failed to parse {filepath}: {e}")
        return None


def generate_new_path(endpoint: str, params: dict) -> str:
    """エンドポイントとパラメータから新しいパスを生成"""
    
    # players
    if "players" in endpoint:
        player_id = params.get("id")
        if player_id:
            # チーム名は不明なので unknown に
            return f"players/unknown/{player_id}.json"
    
    # fixtures/lineups
    if endpoint == "fixtures/lineups":
        fixture_id = params.get("fixture")
        if fixture_id:
            return f"lineups/fixture_{fixture_id}.json"
    
    # fixtures (単一 or リスト)
    if endpoint == "fixtures":
        fixture_id = params.get("id")
        if fixture_id:
            return f"fixtures/id_{fixture_id}.json"
        league = params.get("league")
        date = params.get("date")
        if league and date:
            return f"fixtures/league_{league}_date_{date}.json"
        season = params.get("season")
        if league and season:
            return f"fixtures/league_{league}_season_{season}.json"
    
    # fixtures/headtohead
    if endpoint == "fixtures/headtohead":
        h2h = params.get("h2h")
        if h2h:
            return f"headtohead/{h2h.replace('-', '_vs_')}.json"
    
    # teams/statistics
    if endpoint == "teams/statistics":
        team_id = params.get("team")
        season = params.get("season", "unknown")
        league_id = params.get("league", "unknown")
        if team_id:
            return f"statistics/team_{team_id}_season_{season}_league_{league_id}.json"
    
    # injuries
    if endpoint == "injuries":
        fixture_id = params.get("fixture")
        if fixture_id:
            return f"injuries/fixture_{fixture_id}.json"
    
    return None  # 変換不可


def wrap_with_metadata(data: dict, cached_at: datetime) -> dict:
    """旧形式データに新形式メタデータを付与"""
    return {
        "_cached_at": cached_at.isoformat(),
        "_cache_version": 2,
        "_migrated_from": "legacy",
        **data
    }


def migrate_cache(dry_run: bool = False):
    """キャッシュ移行を実行"""
    
    if not CACHE_DIR.exists():
        print(f"Cache directory not found: {CACHE_DIR}")
        return
    
    print(f"Scanning cache directory: {CACHE_DIR}")
    print(f"Mode: {'DRY RUN' if dry_run else 'MIGRATE'}")
    print("-" * 60)
    
    # 旧形式のファイル（ルート直下のハッシュ付きファイル）を検索
    legacy_files = list(CACHE_DIR.glob("*_*.json"))
    
    # youtube/ サブディレクトリは除外
    legacy_files = [f for f in legacy_files if f.parent == CACHE_DIR]
    
    print(f"Found {len(legacy_files)} legacy cache files")
    print()
    
    migrated = 0
    skipped = 0
    failed = 0
    
    for filepath in legacy_files:
        print(f"Processing: {filepath.name}")
        
        # ファイル解析
        parsed = parse_legacy_cache_file(filepath)
        if not parsed:
            failed += 1
            continue
        
        endpoint = parsed["endpoint"]
        params = parsed["params"]
        
        # 新パス生成
        new_path = generate_new_path(endpoint, params)
        
        if not new_path:
            print(f"  [SKIP] Cannot determine new path for endpoint: {endpoint}")
            skipped += 1
            continue
        
        new_filepath = CACHE_DIR / new_path
        print(f"  -> {new_path}")
        
        if dry_run:
            migrated += 1
            continue
        
        # 新ファイル作成
        try:
            new_filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # メタデータ付与
            wrapped_data = wrap_with_metadata(parsed["data"], parsed["file_mtime"])
            
            with open(new_filepath, 'w', encoding='utf-8') as f:
                json.dump(wrapped_data, f, ensure_ascii=False, indent=2)
            
            # 旧ファイルを .migrated にリネーム（バックアップ）
            backup_path = filepath.with_suffix(".json.migrated")
            shutil.move(filepath, backup_path)
            
            print(f"  [OK] Migrated (backup: {backup_path.name})")
            migrated += 1
            
        except Exception as e:
            print(f"  [ERROR] Failed to migrate: {e}")
            failed += 1
    
    print()
    print("-" * 60)
    print(f"Summary: {migrated} migrated, {skipped} skipped, {failed} failed")
    
    if dry_run:
        print()
        print("This was a dry run. Run without --dry-run to actually migrate.")


def cleanup_backups():
    """移行後のバックアップファイル (.migrated) を削除"""
    backups = list(CACHE_DIR.glob("*.migrated"))
    
    if not backups:
        print("No backup files found.")
        return
    
    print(f"Found {len(backups)} backup files:")
    for f in backups:
        print(f"  {f.name}")
    
    confirm = input("\nDelete all backup files? [y/N]: ")
    if confirm.lower() == 'y':
        for f in backups:
            f.unlink()
            print(f"  Deleted: {f.name}")
        print("Done.")
    else:
        print("Cancelled.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate legacy cache files to new format")
    parser.add_argument("--dry-run", action="store_true", help="Show migration plan without executing")
    parser.add_argument("--cleanup", action="store_true", help="Delete backup files after migration")
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_backups()
    else:
        migrate_cache(dry_run=args.dry_run)
