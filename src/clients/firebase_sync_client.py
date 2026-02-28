"""
Firebase Hosting同期クライアント

Firebase Hostingとの通信を専門に処理する。
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from src.clients.http_client import HttpClient, get_http_client

logger = logging.getLogger(__name__)

FIREBASE_BASE_URL = "https://football-delay-watching-a8830.web.app"
DEFAULT_SHARED_REPORTS_DIR = (
    Path.home() / ".cache" / "football-delay-watching" / "reports"
)


def get_shared_reports_dir() -> Path:
    """共有レポートキャッシュの保存先を返す"""
    configured_dir = os.getenv("FDW_SHARED_REPORTS_DIR")
    if configured_dir:
        return Path(configured_dir).expanduser()
    return DEFAULT_SHARED_REPORTS_DIR


class FirebaseSyncClient:
    """Firebase Hostingとの通信を担当するクライアント"""

    def __init__(
        self,
        base_url: str = FIREBASE_BASE_URL,
        timeout: int = 10,
        http_client: HttpClient | None = None,
        shared_reports_dir: Path | None = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.http_client = http_client or get_http_client()
        self.shared_reports_dir = shared_reports_dir or get_shared_reports_dir()

    def _cache_path_for(self, relative_path: str) -> Path:
        """共有キャッシュ上の保存先を返す"""
        return self.shared_reports_dir / relative_path

    def _write_response_to_path(self, response, output_path: Path) -> None:
        """レスポンス内容をファイルに保存する"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content_type = response.headers.get("Content-Type", "")
        if "image" in content_type or output_path.suffix in [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
        ]:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)

    def _restore_from_cache(self, cache_path: Path, local_path: Path) -> bool:
        """共有キャッシュからローカルに復元する"""
        if not cache_path.exists():
            return False

        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cache_path, local_path)
        logger.info(f"Restored from shared cache: {cache_path.name}")
        return True

    def fetch_manifest(self) -> dict | None:
        """
        Firebase上のmanifest.jsonを取得

        Returns:
            manifest辞書、取得失敗時はNone
        """
        url = f"{self.base_url}/reports/manifest.json?v={datetime.now().timestamp()}"
        try:
            response = self.http_client.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(
                    f"Could not fetch manifest from Firebase: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.warning(f"Failed to fetch manifest from Firebase: {e}")
            return None

    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Firebase上のファイルをダウンロード

        Args:
            remote_path: Firebase上のパス（reports/xxx.html など）
            local_path: ローカル保存先パス

        Returns:
            成功時True
        """
        url = f"{self.base_url}/{remote_path}"
        relative_path = (
            remote_path.removeprefix("reports/")
            if remote_path.startswith("reports/")
            else remote_path
        )
        cache_path = self._cache_path_for(relative_path)
        try:
            response = self.http_client.get(url, timeout=30)
            if response.status_code == 200:
                self._write_response_to_path(response, local_path)
                if cache_path != local_path:
                    self._write_response_to_path(response, cache_path)

                logger.info(f"Downloaded: {remote_path}")
                return True
            else:
                logger.debug(
                    f"Failed to download {remote_path}: HTTP {response.status_code}"
                )
                return False
        except Exception as e:
            logger.warning(f"Failed to download {remote_path}: {e}")
            return False

    def sync_reports(self, local_reports_dir: Path) -> int:
        """
        Firebase上のレポートをローカルに同期

        Args:
            local_reports_dir: ローカルのレポートディレクトリ

        Returns:
            ダウンロードしたファイル数
        """
        manifest = self.fetch_manifest()
        if not manifest:
            return 0

        local_reports_dir.mkdir(parents=True, exist_ok=True)
        (local_reports_dir / "images").mkdir(parents=True, exist_ok=True)

        downloaded = 0
        restored = 0

        # レガシー形式のレポート
        for report in manifest.get("reports", []):
            filename = report.get("file")
            if not filename:
                continue

            local_path = local_reports_dir / filename
            if local_path.exists():
                continue

            if self._restore_from_cache(self._cache_path_for(filename), local_path):
                restored += 1
                continue

            if self.download_file(f"reports/{filename}", local_path):
                downloaded += 1

        failed = 0
        for date_key, date_data in manifest.get("reports_by_date", {}).items():
            for match in date_data.get("matches", []):
                filename = match.get("file")
                if not filename:
                    continue

                local_path = local_reports_dir / filename
                if local_path.exists():
                    continue

                if self._restore_from_cache(self._cache_path_for(filename), local_path):
                    restored += 1
                    continue

                if self.download_file(f"reports/{filename}", local_path):
                    downloaded += 1
                else:
                    failed += 1

        if failed > 0:
            logger.warning(
                f"Failed to sync {failed} files from Firebase (likely 404). Normal for recent files."
            )
        logger.info(f"Restored {restored} files from shared cache")
        logger.info(f"Synced {downloaded} files from Firebase")
        return downloaded
