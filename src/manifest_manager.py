"""
Manifest管理モジュール

manifest.jsonの読み書き・マージロジックを集約。
"""

import json
import logging
from pathlib import Path
from typing import Optional

from config import config
from src.clients.firebase_sync_client import FirebaseSyncClient

logger = logging.getLogger(__name__)

MANIFEST_FILE = Path("public/reports/manifest.json")


class ManifestManager:
    """manifest.jsonの管理を担当"""
    
    def __init__(
        self, 
        manifest_path: Path = MANIFEST_FILE,
        firebase_client: Optional[FirebaseSyncClient] = None
    ):
        self.manifest_path = manifest_path
        self.firebase_client = firebase_client or FirebaseSyncClient()
        self._manifest: dict = {"reports_by_date": {}, "legacy_reports": [], "reports": []}
    
    def load_local(self) -> dict:
        """
        ローカルmanifestを読み込み
        
        Returns:
            manifest辞書
        """
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                self._manifest = json.load(f)
        return self._manifest
    
    def load_with_remote_merge(self) -> dict:
        """
        ローカルとリモートをマージして読み込み
        
        Returns:
            マージ済みmanifest辞書
        """
        # リモートを取得
        remote_manifest = self.firebase_client.fetch_manifest()
        if remote_manifest:
            self._manifest["reports_by_date"] = remote_manifest.get("reports_by_date", {})
            self._manifest["legacy_reports"] = remote_manifest.get("legacy_reports", [])
            self._manifest["reports"] = remote_manifest.get("reports", [])
            logger.info("Fetched existing manifest from Firebase")
        
        # ローカルをマージ
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                local_manifest = json.load(f)
            
            # reports_by_date のマージ
            local_reports_by_date = local_manifest.get("reports_by_date", {})
            for date_key, date_data in local_reports_by_date.items():
                if date_key not in self._manifest["reports_by_date"]:
                    self._manifest["reports_by_date"][date_key] = date_data
                else:
                    # 試合のマージ（fixture_idとfileで重複除去）
                    existing_keys = {
                        f"{m.get('fixture_id')}_{m.get('file')}" 
                        for m in self._manifest["reports_by_date"][date_key].get("matches", [])
                    }
                    for match in date_data.get("matches", []):
                        key = f"{match.get('fixture_id')}_{match.get('file')}"
                        if key not in existing_keys:
                            self._manifest["reports_by_date"][date_key]["matches"].append(match)
            
            self._manifest["legacy_reports"].extend(local_manifest.get("legacy_reports", []))
            self._manifest["reports"].extend(local_manifest.get("reports", []))
        
        return self._manifest
    
    def add_legacy_report(self, report_datetime: str, filename: str, timestamp: str) -> None:
        """
        レガシー形式のレポートを追加
        
        Args:
            report_datetime: レポート日時
            filename: ファイル名
            timestamp: 生成タイムスタンプ
        """
        new_report = {
            "datetime": report_datetime, 
            "file": filename, 
            "generated": timestamp,
            "is_debug": config.DEBUG_MODE,
            "is_mock": config.USE_MOCK_DATA
        }
        self._manifest.setdefault("reports", []).append(new_report)
    
    def add_match_entries(
        self, 
        match_entries: list, 
        generation_datetime: str
    ) -> None:
        """
        試合エントリを追加
        
        Args:
            match_entries: 試合エントリのリスト
            generation_datetime: 生成日時
        """
        reports_by_date = self._manifest.setdefault("reports_by_date", {})
        
        for entry in match_entries:
            match_date = entry.get("match_date") or entry.get("kickoff_local", "").split()[0]
            
            if match_date not in reports_by_date:
                reports_by_date[match_date] = {
                    "generation_datetime": generation_datetime,
                    "is_debug": config.DEBUG_MODE,
                    "is_mock": config.USE_MOCK_DATA,
                    "matches": []
                }
            
            reports_by_date[match_date]["matches"].append(entry)
    
    def migrate_legacy_reports(self) -> None:
        """旧形式レポート（reports）をlegacy_reportsに移行"""
        legacy_reports = self._manifest.setdefault("legacy_reports", [])
        old_reports = self._manifest.get("reports", [])
        
        # 重複除去してlegacy_reportsに統合
        legacy_seen = {r.get("datetime") for r in legacy_reports}
        for r in old_reports:
            if r.get("datetime") not in legacy_seen:
                legacy_reports.append(r)
                legacy_seen.add(r.get("datetime"))
        
        # 日時でソート（新しい順）
        legacy_reports.sort(key=lambda x: x.get("datetime", ""), reverse=True)
        
        self._manifest["legacy_reports"] = legacy_reports
    
    def deduplicate_legacy_reports(self) -> None:
        """レガシーレポートの重複を除去しソート"""
        reports = self._manifest.get("reports", [])
        
        seen = set()
        unique_reports = []
        for r in reports:
            dt = r.get("datetime")
            if dt and dt not in seen:
                seen.add(dt)
                unique_reports.append(r)
        
        unique_reports.sort(key=lambda x: x.get("datetime", ""), reverse=True)
        self._manifest["reports"] = unique_reports
    
    def save(self) -> None:
        """manifestを保存"""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # reportsフィールドを除外して保存（legacy_reportsに移行済み）
        manifest_to_save = {
            "reports_by_date": self._manifest.get("reports_by_date", {}),
            "legacy_reports": self._manifest.get("legacy_reports", [])
        }
        
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_to_save, f, ensure_ascii=False, indent=2)
        
        total_matches = sum(
            len(v.get("matches", [])) 
            for v in self._manifest.get("reports_by_date", {}).values()
        )
        logger.info(
            f"Updated manifest: {len(self._manifest.get('reports_by_date', {}))} dates, "
            f"{total_matches} matches, {len(self._manifest.get('legacy_reports', []))} legacy reports"
        )
    
    @property
    def manifest(self) -> dict:
        """現在のmanifest辞書を取得"""
        return self._manifest
