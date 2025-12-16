"""
APIレスポンスキャッシュモジュール

ローカルファイルまたはGCSをバックエンドとして使用可能。
環境変数 CACHE_BACKEND で切り替え:
  - "local" (デフォルト): api_cache/ ディレクトリに保存
  - "gcs": Google Cloud Storageに保存
"""

import os
import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import requests
from config import config

logger = logging.getLogger(__name__)

# ローカルキャッシュディレクトリ
CACHE_DIR = Path("api_cache")

# GCS設定
GCS_BUCKET_NAME = os.getenv("GCS_CACHE_BUCKET", "football-delay-watching-cache")
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "local")  # "local" or "gcs"

# GCSクライアント（遅延初期化）
_gcs_client = None
_gcs_bucket = None


def _get_gcs_client():
    """GCSクライアントを遅延初期化して返す"""
    global _gcs_client, _gcs_bucket
    if _gcs_client is None:
        try:
            from google.cloud import storage
            _gcs_client = storage.Client()
            _gcs_bucket = _gcs_client.bucket(GCS_BUCKET_NAME)
            logger.info(f"GCS client initialized for bucket: {GCS_BUCKET_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise
    return _gcs_bucket


def _sanitize_name(name: str) -> str:
    """ファイル名・ディレクトリ名として安全な文字列に変換"""
    # スペースをアンダースコアに、特殊文字を除去
    safe = name.replace(" ", "_").replace("'", "").replace("&", "and")
    return "".join(c for c in safe if c.isalnum() or c in ('_', '-'))


def _get_cache_key(url: str, params: Dict[str, Any]) -> str:
    """URLとパラメータから一意のキャッシュキー（ファイル名）を生成"""
    params_str = json.dumps(params, sort_keys=True)
    base_str = f"{url}{params_str}"
    md5_hash = hashlib.md5(base_str.encode('utf-8')).hexdigest()
    
    url_suffix = url.split('/')[-1] if '/' in url else "api"
    url_suffix = "".join(c for c in url_suffix if c.isalnum() or c in ('_', '-'))
    
    return f"{url_suffix}_{md5_hash}.json"


def _get_gcs_path(endpoint: str, identifier: str, team_name: str = None) -> str:
    """
    GCS用のパスを生成
    
    構造:
      - players/{team_name}/{player_id}.json
      - fixtures/{hash}.json
      - lineups/{hash}.json
      - その他/{hash}.json
    """
    if endpoint == "players" and team_name:
        safe_team = _sanitize_name(team_name)
        return f"players/{safe_team}/{identifier}.json"
    else:
        return f"{endpoint}/{identifier}.json"


class CachedResponse:
    """キャッシュから読み込んだデータをrequests.Responseのように扱うクラス"""
    def __init__(self, json_data):
        self._json_data = json_data
        self.status_code = 200
        self.ok = True
        
    @property
    def headers(self):
        return {}
        
    def json(self):
        return self._json_data
    
    def raise_for_status(self):
        pass


def _read_from_gcs(gcs_path: str) -> Optional[dict]:
    """GCSからJSONを読み込む"""
    try:
        bucket = _get_gcs_client()
        blob = bucket.blob(gcs_path)
        if blob.exists():
            content = blob.download_as_text()
            return json.loads(content)
    except Exception as e:
        logger.warning(f"Failed to read from GCS {gcs_path}: {e}")
    return None


def _write_to_gcs(gcs_path: str, data: dict):
    """GCSにJSONを書き込む"""
    try:
        bucket = _get_gcs_client()
        blob = bucket.blob(gcs_path)
        blob.upload_from_string(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type='application/json'
        )
        logger.debug(f"Cache saved to GCS: {gcs_path}")
    except Exception as e:
        logger.warning(f"Failed to write to GCS {gcs_path}: {e}")


def _read_from_local(cache_path: Path) -> Optional[dict]:
    """ローカルファイルからJSONを読み込む"""
    try:
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read local cache {cache_path}: {e}")
    return None


def _write_to_local(cache_path: Path, data: dict):
    """ローカルファイルにJSONを書き込む"""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"Cache saved to local: {cache_path}")
    except Exception as e:
        logger.warning(f"Failed to write local cache {cache_path}: {e}")


def get_with_cache(
    url: str, 
    headers: Dict[str, str], 
    params: Dict[str, Any] = None,
    team_name: str = None
) -> requests.Response:
    """
    キャッシュ機能付きのGETリクエスト
    
    Args:
        url: APIエンドポイントURL
        headers: リクエストヘッダー
        params: クエリパラメータ
        team_name: チーム名（playersエンドポイント用、チーム別ディレクトリに保存）
    
    Returns:
        requests.Response または CachedResponse
    """
    if params is None:
        params = {}
        
    start_time = time.time()
    
    # キャッシュ無効時は通常リクエスト
    if not config.USE_API_CACHE:
        response = requests.get(url, headers=headers, params=params)
        duration = time.time() - start_time
        logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: DISABLED")
        return response

    # キャッシュキーの生成
    cache_key = _get_cache_key(url, params)
    endpoint = url.split('/')[-1] if '/' in url else "api"
    endpoint = "".join(c for c in endpoint if c.isalnum() or c in ('_', '-'))
    
    # バックエンドに応じたパス生成
    if CACHE_BACKEND == "gcs":
        # GCSの場合: players/{team}/{id}.json または {endpoint}/{hash}.json
        if endpoint == "players" and team_name and "id" in params:
            gcs_path = _get_gcs_path("players", str(params["id"]), team_name)
        else:
            hash_part = cache_key.replace(f"{endpoint}_", "").replace(".json", "")
            gcs_path = _get_gcs_path(endpoint, hash_part)
        
        # GCSから読み込み
        cached_data = _read_from_gcs(gcs_path)
        if cached_data:
            duration = time.time() - start_time
            logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: GCS HIT ({gcs_path})")
            return CachedResponse(cached_data)
    else:
        # ローカルの場合
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = CACHE_DIR / cache_key
        
        cached_data = _read_from_local(cache_path)
        if cached_data:
            duration = time.time() - start_time
            logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: HIT ({cache_key})")
            return CachedResponse(cached_data)
    
    # キャッシュミス -> APIリクエスト
    try:
        response = requests.get(url, headers=headers, params=params)
        duration = time.time() - start_time
        backend_name = "GCS" if CACHE_BACKEND == "gcs" else "LOCAL"
        logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: MISS ({backend_name})")
        
        # 成功時のみキャッシュ保存
        if response.status_code == 200:
            data = response.json()
            if CACHE_BACKEND == "gcs":
                _write_to_gcs(gcs_path, data)
            else:
                _write_to_local(cache_path, data)
                
        return response
        
    except Exception as e:
        logger.error(f"[API] Request failed: {e}")
        raise
