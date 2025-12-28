#!/usr/bin/env python
"""
Firebase Hosting からレポートを同期するスクリプト

デプロイ前に実行して、Firebase上にのみ存在するレポートをダウンロードし、
ローカルの public/reports/ とマージする。

使用方法:
    python scripts/sync_firebase_reports.py

動作:
    1. Firebase Hosting から manifest.json を取得
    2. 各レポートHTMLをダウンロード（ローカルにないもののみ）
    3. imagesフォルダの画像もダウンロード
    4. manifest.json をマージ
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Set

import requests

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 設定
FIREBASE_URL = "https://football-delay-watching-a8830.web.app"
LOCAL_REPORTS_DIR = Path("public/reports")
LOCAL_IMAGES_DIR = LOCAL_REPORTS_DIR / "images"


def fetch_remote_manifest() -> Dict:
    """Firebase上のmanifest.jsonを取得"""
    url = f"{FIREBASE_URL}/reports/manifest.json"
    logger.info(f"Fetching remote manifest: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch remote manifest: {response.status_code}")
            return {"reports": []}
    except Exception as e:
        logger.error(f"Error fetching remote manifest: {e}")
        return {"reports": []}


def fetch_local_manifest() -> Dict:
    """ローカルのmanifest.jsonを取得"""
    manifest_path = LOCAL_REPORTS_DIR / "manifest.json"
    
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read local manifest: {e}")
    
    return {"reports": []}


def get_local_files() -> Set[str]:
    """ローカルに存在するファイル名のセットを取得"""
    files = set()
    
    if LOCAL_REPORTS_DIR.exists():
        for f in LOCAL_REPORTS_DIR.iterdir():
            if f.is_file() and f.suffix == ".html":
                files.add(f.name)
    
    return files


def download_file(remote_path: str, local_path: Path) -> bool:
    """ファイルをダウンロード"""
    url = f"{FIREBASE_URL}/reports/{remote_path}"
    
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Downloaded: {remote_path}")
            return True
        else:
            logger.warning(f"Failed to download {remote_path}: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error downloading {remote_path}: {e}")
        return False


def merge_manifests(local: Dict, remote: Dict) -> Dict:
    """
    マニフェストをマージ（新構造対応）
    
    新構造:
    {
        "reports_by_date": {...},  # 試合別レポート
        "legacy_reports": [...]     # 旧形式レポート
    }
    
    旧構造:
    {
        "reports": [...]
    }
    """
    # 新構造のベース
    merged = {
        "reports_by_date": {},
        "legacy_reports": []
    }
    
    # --- reports_by_date のマージ ---
    # ローカル優先（新しく生成したもの）
    local_reports_by_date = local.get("reports_by_date", {})
    remote_reports_by_date = remote.get("reports_by_date", {})
    
    # リモートから取得
    for date_key, date_data in remote_reports_by_date.items():
        if date_key not in merged["reports_by_date"]:
            merged["reports_by_date"][date_key] = date_data
    
    # ローカルで上書き（ローカル優先）
    for date_key, date_data in local_reports_by_date.items():
        if date_key not in merged["reports_by_date"]:
            merged["reports_by_date"][date_key] = date_data
        else:
            # 試合のマージ（fixture_idで重複除去）
            existing_ids = {m.get("fixture_id") for m in merged["reports_by_date"][date_key].get("matches", [])}
            for match in date_data.get("matches", []):
                if match.get("fixture_id") not in existing_ids:
                    merged["reports_by_date"][date_key]["matches"].append(match)
    
    # --- legacy_reports のマージ ---
    # 旧形式（reports）も含めてすべてlegacy_reportsに統合
    legacy_files = {}
    
    # リモートのlegacy_reports
    for report in remote.get("legacy_reports", []):
        file_name = report.get("file")
        if file_name:
            legacy_files[file_name] = report
    
    # リモートの旧形式（reports）
    for report in remote.get("reports", []):
        file_name = report.get("file")
        if file_name and file_name not in legacy_files:
            legacy_files[file_name] = report
    
    # ローカルのlegacy_reports
    for report in local.get("legacy_reports", []):
        file_name = report.get("file")
        if file_name and file_name not in legacy_files:
            legacy_files[file_name] = report
    
    # ローカルの旧形式（reports）
    for report in local.get("reports", []):
        file_name = report.get("file")
        if file_name and file_name not in legacy_files:
            legacy_files[file_name] = report
    
    # 日付でソート（新しい順）
    merged["legacy_reports"] = sorted(
        legacy_files.values(),
        key=lambda r: r.get("datetime", r.get("file", "")),
        reverse=True
    )
    
    return merged


def sync_reports() -> None:
    """メイン同期処理"""
    logger.info("=== Firebase Reports Sync ===")
    
    # ディレクトリ作成
    LOCAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # マニフェスト取得
    remote_manifest = fetch_remote_manifest()
    local_manifest = fetch_local_manifest()
    
    remote_reports = remote_manifest.get("reports", [])
    logger.info(f"Remote reports: {len(remote_reports)}")
    
    # ローカルファイル確認
    local_files = get_local_files()
    logger.info(f"Local reports: {len(local_files)}")
    
    # 不足しているレポートをダウンロード
    downloaded_count = 0
    for report in remote_reports:
        file_name = report.get("file")
        if file_name and file_name not in local_files:
            local_path = LOCAL_REPORTS_DIR / file_name
            if download_file(file_name, local_path):
                downloaded_count += 1
    
    logger.info(f"Downloaded {downloaded_count} new reports")
    
    # マニフェストをマージして保存
    merged = merge_manifests(local_manifest, remote_manifest)
    manifest_path = LOCAL_REPORTS_DIR / "manifest.json"
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)
    
    logger.info(f"Manifest updated: {len(merged['reports'])} reports total")
    logger.info("=== Sync Complete ===")


if __name__ == "__main__":
    sync_reports()
