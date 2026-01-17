"""
キャッシュストア抽象基底クラスと実装

ストレージバックエンド（GCS/Local）を抽象化し、
依存性注入（DI）によるテスト容易性と拡張性を提供する。
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheStore(ABC):
    """キャッシュストアの抽象基底クラス"""

    @abstractmethod
    def read(self, path: str) -> dict | None:
        """
        キャッシュからデータを読み込む

        Args:
            path: キャッシュパス（例: "players/12345.json"）

        Returns:
            キャッシュデータ（存在しない場合はNone）
        """
        pass

    @abstractmethod
    def write(self, path: str, data: dict) -> None:
        """
        キャッシュにデータを書き込む

        Args:
            path: キャッシュパス
            data: 保存するデータ
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        キャッシュが存在するか確認

        Args:
            path: キャッシュパス

        Returns:
            存在する場合True
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """
        キャッシュを削除

        Args:
            path: キャッシュパス

        Returns:
            削除に成功した場合True
        """
        pass


class LocalCacheStore(CacheStore):
    """ローカルファイルシステムを使用するキャッシュストア"""

    def __init__(self, base_dir: Path):
        """
        Args:
            base_dir: キャッシュのベースディレクトリ
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        return self.base_dir / path

    def read(self, path: str) -> dict | None:
        cache_path = self._get_full_path(path)
        try:
            if cache_path.exists():
                with open(cache_path, encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read local cache {cache_path}: {e}")
        return None

    def write(self, path: str, data: dict) -> None:
        cache_path = self._get_full_path(path)
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cache saved to local: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to write local cache {cache_path}: {e}")

    def exists(self, path: str) -> bool:
        return self._get_full_path(path).exists()

    def delete(self, path: str) -> bool:
        cache_path = self._get_full_path(path)
        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"Local cache deleted: {cache_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete local cache {cache_path}: {e}")
        return False


class GcsCacheStore(CacheStore):
    """Google Cloud Storageを使用するキャッシュストア"""

    def __init__(self, bucket_name: str):
        """
        Args:
            bucket_name: GCSバケット名
        """
        self.bucket_name = bucket_name
        self._client = None
        self._bucket = None

    def _get_bucket(self):
        """GCSバケットを遅延初期化して返す"""
        if self._bucket is None:
            try:
                from google.cloud import storage

                self._client = storage.Client()
                self._bucket = self._client.bucket(self.bucket_name)
                logger.info(f"GCS client initialized for bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._bucket

    def read(self, path: str) -> dict | None:
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            if blob.exists():
                content = blob.download_as_text()
                return json.loads(content)
        except Exception as e:
            logger.warning(f"Failed to read from GCS {path}: {e}")
        return None

    def write(self, path: str, data: dict) -> None:
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            blob.upload_from_string(
                json.dumps(data, ensure_ascii=False, indent=2),
                content_type="application/json",
            )
            logger.debug(f"Cache saved to GCS: {path}")
        except Exception as e:
            logger.warning(f"Failed to write to GCS {path}: {e}")

    def exists(self, path: str) -> bool:
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            return blob.exists()
        except Exception as e:
            logger.warning(f"Failed to check GCS existence {path}: {e}")
            return False

    def delete(self, path: str) -> bool:
        try:
            bucket = self._get_bucket()
            blob = bucket.blob(path)
            if blob.exists():
                blob.delete()
                logger.info(f"GCS cache deleted: {path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete GCS cache {path}: {e}")
        return False


def create_cache_store(backend: str = None) -> CacheStore:
    """
    設定に基づいてCacheStoreインスタンスを生成するファクトリ関数

    Args:
        backend: "gcs" または "local"（省略時は設定から取得）

    Returns:
        CacheStoreインスタンス
    """
    from settings.cache_config import CACHE_BACKEND, GCS_BUCKET_NAME, LOCAL_CACHE_DIR

    backend = backend or CACHE_BACKEND

    if backend == "gcs":
        return GcsCacheStore(GCS_BUCKET_NAME)
    else:
        return LocalCacheStore(LOCAL_CACHE_DIR)
