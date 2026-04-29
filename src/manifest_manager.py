"""
Manifest管理モジュール

manifest.jsonの読み書き・マージロジックを集約。
"""

import json
import logging
import re
from pathlib import Path

from config import config
from src.clients.firebase_sync_client import FirebaseSyncClient

logger = logging.getLogger(__name__)

MANIFEST_FILE = Path("public/reports/manifest.json")

# レポートファイル名末尾の `_YYYYMMDD_HHMMSS.html` を抽出する
_FILE_TIMESTAMP_RE = re.compile(r"_(\d{8})_(\d{6})\.html$")


def _extract_file_timestamp(file_name: str | None) -> str:
    """レポートファイル名から `YYYYMMDDHHMMSS` 形式のタイムスタンプを抽出する。

    タイムスタンプ部分が無い場合は空文字を返す（最古として扱う）。
    """
    if not file_name:
        return ""
    match = _FILE_TIMESTAMP_RE.search(file_name)
    if not match:
        return ""
    return match.group(1) + match.group(2)


def prune_missing_manifest_entries(
    manifest: dict,
    reports_dir: Path = MANIFEST_FILE.parent,
) -> tuple[dict, list[str]]:
    """存在しないHTMLを参照するmanifestエントリを除外する"""
    reports_by_date = manifest.get("reports_by_date", {})
    pruned_reports_by_date = {}
    removed_files: list[str] = []

    for date_key, date_data in reports_by_date.items():
        matches = []
        for match in date_data.get("matches", []):
            file_name = match.get("file")
            if not file_name:
                matches.append(match)
                continue

            if (reports_dir / file_name).exists():
                matches.append(match)
                continue

            removed_files.append(file_name)

        if matches:
            pruned_reports_by_date[date_key] = {**date_data, "matches": matches}

    pruned_manifest = {**manifest, "reports_by_date": pruned_reports_by_date}
    return pruned_manifest, removed_files


def dedupe_matches_by_fixture_id(manifest: dict) -> tuple[dict, list[str]]:
    """同一 `fixture_id` のエントリは最新ファイル 1 件だけ残す。

    「最新」はファイル名末尾の `_YYYYMMDD_HHMMSS` を文字列比較した最大値で判定する。
    タイムスタンプを抽出できないエントリは最古とみなし、同タイムスタンプの場合は
    後勝ち（後から追加された方を採用）とする。

    `fixture_id` 自体が無いエントリは触らずに保持する。

    Returns:
        (deduped_manifest, dropped_files)
    """
    reports_by_date = manifest.get("reports_by_date", {})

    # fixture_id 単位で「最新」とみなすエントリの位置 (date_key, idx) を特定
    latest_index: dict[str, tuple[str, int, str]] = {}
    for date_key, date_data in reports_by_date.items():
        for idx, match in enumerate(date_data.get("matches", [])):
            fixture_id = match.get("fixture_id")
            if fixture_id is None:
                continue
            fid_key = str(fixture_id)
            new_ts = _extract_file_timestamp(match.get("file"))
            existing = latest_index.get(fid_key)
            if existing is None or new_ts >= existing[2]:
                latest_index[fid_key] = (date_key, idx, new_ts)

    dropped_files: list[str] = []
    deduped_reports_by_date: dict = {}
    for date_key, date_data in reports_by_date.items():
        new_matches = []
        for idx, match in enumerate(date_data.get("matches", [])):
            fixture_id = match.get("fixture_id")
            if fixture_id is None:
                new_matches.append(match)
                continue
            fid_key = str(fixture_id)
            chosen_date, chosen_idx, _ = latest_index[fid_key]
            if chosen_date == date_key and chosen_idx == idx:
                new_matches.append(match)
            else:
                file_name = match.get("file")
                if file_name:
                    dropped_files.append(file_name)

        if new_matches:
            deduped_reports_by_date[date_key] = {**date_data, "matches": new_matches}

    deduped_manifest = {**manifest, "reports_by_date": deduped_reports_by_date}
    return deduped_manifest, dropped_files


class ManifestManager:
    """manifest.jsonの管理を担当"""

    def __init__(
        self,
        manifest_path: Path = MANIFEST_FILE,
        firebase_client: FirebaseSyncClient | None = None,
    ):
        self.manifest_path = manifest_path
        self.firebase_client = firebase_client or FirebaseSyncClient()
        self._manifest: dict = {"reports_by_date": {}}

    def load_local(self) -> dict:
        """
        ローカルmanifestを読み込み

        Returns:
            manifest辞書
        """
        if self.manifest_path.exists():
            with open(self.manifest_path, encoding="utf-8") as f:
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
            self._manifest["reports_by_date"] = remote_manifest.get(
                "reports_by_date", {}
            )
            logger.info("Fetched existing manifest from Firebase")

        # ローカルをマージ
        if self.manifest_path.exists():
            with open(self.manifest_path, encoding="utf-8") as f:
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
                        for m in self._manifest["reports_by_date"][date_key].get(
                            "matches", []
                        )
                    }
                    for match in date_data.get("matches", []):
                        key = f"{match.get('fixture_id')}_{match.get('file')}"
                        if key not in existing_keys:
                            self._manifest["reports_by_date"][date_key][
                                "matches"
                            ].append(match)

        # 同一 fixture_id の旧エントリを除去し、最新ファイルだけを残す
        self._manifest, dropped_files = dedupe_matches_by_fixture_id(self._manifest)
        if dropped_files:
            logger.info(
                "Dropped %d stale fixture entries during merge: %s",
                len(dropped_files),
                ", ".join(dropped_files[:5]),
            )

        return self._manifest

    def add_match_entries(self, match_entries: list, generation_datetime: str) -> None:
        """
        試合エントリを追加

        Args:
            match_entries: 試合エントリのリスト
            generation_datetime: 生成日時
        """
        reports_by_date = self._manifest.setdefault("reports_by_date", {})

        for entry in match_entries:
            match_date = (
                entry.get("match_date") or entry.get("kickoff_local", "").split()[0]
            )

            if match_date not in reports_by_date:
                reports_by_date[match_date] = {
                    "generation_datetime": generation_datetime,
                    "is_debug": config.DEBUG_MODE,
                    "is_mock": config.USE_MOCK_DATA,
                    "matches": [],
                }

            reports_by_date[match_date]["matches"].append(entry)

    def save(self) -> None:
        """manifestを保存"""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest, removed_files = prune_missing_manifest_entries(
            self._manifest,
            self.manifest_path.parent,
        )

        if removed_files:
            logger.info(
                "Pruned %d missing manifest entries: %s",
                len(removed_files),
                ", ".join(removed_files[:5]),
            )

        # 同一 fixture_id のエントリは最新ファイルだけを残す
        self._manifest, dropped_files = dedupe_matches_by_fixture_id(self._manifest)
        if dropped_files:
            logger.info(
                "Dropped %d duplicate fixture entries: %s",
                len(dropped_files),
                ", ".join(dropped_files[:5]),
            )

        # manifestを保存
        manifest_to_save = {
            "reports_by_date": self._manifest.get("reports_by_date", {})
        }

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_to_save, f, ensure_ascii=False, indent=2)

        total_matches = sum(
            len(v.get("matches", []))
            for v in self._manifest.get("reports_by_date", {}).values()
        )
        logger.info(
            f"Updated manifest: {len(self._manifest.get('reports_by_date', {}))} dates, "
            f"{total_matches} matches"
        )

    @property
    def manifest(self) -> dict:
        """現在のmanifest辞書を取得"""
        return self._manifest
