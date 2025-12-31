"""
Firebase Hosting同期クライアント

Firebase Hostingとの通信を専門に処理する。
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

FIREBASE_BASE_URL = "https://football-delay-watching-a8830.web.app"


class FirebaseSyncClient:
    """Firebase Hostingとの通信を担当するクライアント"""
    
    def __init__(self, base_url: str = FIREBASE_BASE_URL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
    
    def fetch_manifest(self) -> Optional[dict]:
        """
        Firebase上のmanifest.jsonを取得
        
        Returns:
            manifest辞書、取得失敗時はNone
        """
        url = f"{self.base_url}/reports/manifest.json?v={datetime.now().timestamp()}"
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Could not fetch manifest from Firebase: {response.status_code}")
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
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # バイナリかテキストかで処理を分岐
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type or local_path.suffix in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                else:
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                
                logger.info(f"Downloaded: {remote_path}")
                return True
            else:
                logger.warning(f"Failed to download {remote_path}: HTTP {response.status_code}")
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
        
        # レガシー形式のレポート
        for report in manifest.get("reports", []):
            filename = report.get("file")
            if not filename:
                continue
            
            local_path = local_reports_dir / filename
            if local_path.exists():
                continue
            
            if self.download_file(f"reports/{filename}", local_path):
                downloaded += 1
        
        # 新形式のレポート
        for date_key, date_data in manifest.get("reports_by_date", {}).items():
            for match in date_data.get("matches", []):
                filename = match.get("file")
                if not filename:
                    continue
                
                local_path = local_reports_dir / filename
                if local_path.exists():
                    continue
                
                if self.download_file(f"reports/{filename}", local_path):
                    downloaded += 1
        
        logger.info(f"Synced {downloaded} files from Firebase")
        return downloaded
