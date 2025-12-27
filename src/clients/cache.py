"""
APIレスポンスキャッシュモジュール

ローカルファイルまたはGCSをバックエンドとして使用可能。
環境変数 CACHE_BACKEND で切り替え:
  - "local" (デフォルト): api_cache/ ディレクトリに保存
  - "gcs": Google Cloud Storageに保存

機能:
  - 可読なファイル名でキャッシュ保存
  - エンドポイント別TTL（有効期限）チェック
  - 既存ハッシュ形式との後方互換性
"""

import os
import json
import hashlib
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import requests
from config import config

logger = logging.getLogger(__name__)

# ローカルキャッシュディレクトリ
CACHE_DIR = Path("api_cache")

# GCS設定
GCS_BUCKET_NAME = os.getenv("GCS_CACHE_BUCKET", "football-delay-watching-cache")
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "gcs")  # "local" or "gcs" (default: gcs)

# エンドポイント別TTL設定（日数）
# None = 無期限、0 = キャッシュしない
ENDPOINT_TTL_DAYS = {
    "players": None,      # 無期限（国籍等は静的）
    "lineups": None,      # 無期限（試合後は確定）
    "fixtures": 10,       # 10日間
    "headtohead": 10,     # 10日間
    "statistics": 10,     # 10日間
    "injuries": 0,        # キャッシュしない
}

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


def _get_endpoint_from_url(url: str) -> str:
    """URLからエンドポイント名を抽出"""
    # 例: https://v3.football.api-sports.io/fixtures/lineups -> lineups
    # 例: https://v3.football.api-sports.io/fixtures -> fixtures
    # 例: https://v3.football.api-sports.io/fixtures/headtohead -> headtohead
    url_suffix = url.split('/')[-1] if '/' in url else "api"
    return "".join(c for c in url_suffix if c.isalnum() or c in ('_', '-'))


def _get_readable_cache_path(url: str, params: Dict[str, Any], team_name: str = None) -> Tuple[str, str]:
    """
    URLとパラメータから可読なキャッシュパスを生成
    
    Returns:
        (endpoint, readable_path) のタプル
    """
    endpoint = _get_endpoint_from_url(url)
    
    # エンドポイント別に可読なパスを生成
    if endpoint == "players" and "id" in params:
        # players/{player_id}.json（チーム名は使用しない）
        player_id = params["id"]
        return endpoint, f"players/{player_id}.json"
    
    elif endpoint == "lineups" and "fixture" in params:
        # lineups/fixture_{fixture_id}.json
        fixture_id = params["fixture"]
        return endpoint, f"lineups/fixture_{fixture_id}.json"
    
    elif endpoint == "fixtures":
        if "id" in params:
            # fixtures/id_{fixture_id}.json (単一試合)
            fixture_id = params["id"]
            return endpoint, f"fixtures/id_{fixture_id}.json"
        elif "league" in params and "date" in params:
            # fixtures/league_{league_id}_date_{date}.json
            league_id = params["league"]
            date = params["date"]
            return endpoint, f"fixtures/league_{league_id}_date_{date}.json"
        elif "league" in params and "season" in params:
            # fixtures/league_{league_id}_season_{season}.json
            league_id = params["league"]
            season = params["season"]
            return endpoint, f"fixtures/league_{league_id}_season_{season}.json"
    
    elif endpoint == "headtohead" and "h2h" in params:
        # headtohead/{team1_id}_vs_{team2_id}.json
        h2h = params["h2h"]
        return endpoint, f"headtohead/{h2h.replace('-', '_vs_')}.json"
    
    elif endpoint == "statistics" and "team" in params:
        # statistics/team_{team_id}_season_{season}_league_{league_id}.json
        team_id = params["team"]
        season = params.get("season", "unknown")
        league_id = params.get("league", "unknown")
        return endpoint, f"statistics/team_{team_id}_season_{season}_league_{league_id}.json"
    
    elif endpoint == "injuries" and "fixture" in params:
        # injuries/fixture_{fixture_id}.json
        fixture_id = params["fixture"]
        return endpoint, f"injuries/fixture_{fixture_id}.json"
    
    # フォールバック: ハッシュベースのパス
    params_str = json.dumps(params, sort_keys=True)
    base_str = f"{url}{params_str}"
    md5_hash = hashlib.md5(base_str.encode('utf-8')).hexdigest()
    return endpoint, f"{endpoint}/{md5_hash}.json"


def _get_legacy_cache_key(url: str, params: Dict[str, Any]) -> str:
    """旧形式（ハッシュベース）のキャッシュキーを生成（後方互換用）"""
    params_str = json.dumps(params, sort_keys=True)
    base_str = f"{url}{params_str}"
    md5_hash = hashlib.md5(base_str.encode('utf-8')).hexdigest()
    
    url_suffix = url.split('/')[-1] if '/' in url else "api"
    url_suffix = "".join(c for c in url_suffix if c.isalnum() or c in ('_', '-'))
    
    return f"{url_suffix}_{md5_hash}.json"


def _check_ttl(cached_data: dict, endpoint: str) -> bool:
    """
    TTLチェック: キャッシュが有効期限内かどうかを判定
    
    Returns:
        True = 有効、False = 期限切れ
    """
    ttl_days = ENDPOINT_TTL_DAYS.get(endpoint)
    
    # None = 無期限
    if ttl_days is None:
        return True
    
    # 0 = キャッシュしない
    if ttl_days == 0:
        return False
    
    # cached_at が含まれていない場合は旧形式 → 有効とみなす（移行期間中）
    cached_at_str = cached_data.get("_cached_at")
    if not cached_at_str:
        logger.debug(f"Cache missing _cached_at, treating as valid (legacy format)")
        return True
    
    try:
        cached_at = datetime.fromisoformat(cached_at_str)
        expiry = cached_at + timedelta(days=ttl_days)
        is_valid = datetime.now() < expiry
        
        if not is_valid:
            logger.info(f"Cache expired: cached_at={cached_at_str}, ttl={ttl_days}d")
        
        return is_valid
    except Exception as e:
        logger.warning(f"Failed to parse cached_at: {e}")
        return True  # パース失敗時は有効とみなす


def _wrap_with_metadata(data: dict) -> dict:
    """キャッシュデータにメタデータ（cached_at）を付与"""
    return {
        "_cached_at": datetime.now().isoformat(),
        "_cache_version": 2,  # 新形式のバージョン
        **data
    }


def _unwrap_metadata(cached_data: dict) -> dict:
    """メタデータを除去して元のデータを返す"""
    result = {k: v for k, v in cached_data.items() if not k.startswith("_")}
    return result if result else cached_data


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
    
    # エンドポイント抽出
    endpoint = _get_endpoint_from_url(url)
    
    # injuriesはキャッシュしない
    if ENDPOINT_TTL_DAYS.get(endpoint) == 0:
        response = requests.get(url, headers=headers, params=params)
        duration = time.time() - start_time
        logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: DISABLED (no-cache endpoint)")
        return response
    
    # キャッシュ無効時は通常リクエスト
    if not config.USE_API_CACHE:
        response = requests.get(url, headers=headers, params=params)
        duration = time.time() - start_time
        logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: DISABLED")
        return response

    # 可読なキャッシュパスを生成
    endpoint, readable_path = _get_readable_cache_path(url, params, team_name)
    
    # 旧形式のキャッシュキー（後方互換用）
    legacy_key = _get_legacy_cache_key(url, params)
    
    # バックエンドに応じたキャッシュ読み込み
    if CACHE_BACKEND == "gcs":
        # 新形式を優先で試行
        cached_data = _read_from_gcs(readable_path)
        cache_path_used = readable_path
        
        # 新形式がなければ旧形式を試行（後方互換）
        if cached_data is None:
            legacy_gcs_path = f"{endpoint}/{legacy_key.replace(f'{endpoint}_', '').replace('.json', '')}.json"
            cached_data = _read_from_gcs(legacy_gcs_path)
            if cached_data:
                cache_path_used = legacy_gcs_path + " (legacy)"
        
        if cached_data and _check_ttl(cached_data, endpoint):
            duration = time.time() - start_time
            logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: GCS HIT ({cache_path_used})")
            return CachedResponse(_unwrap_metadata(cached_data))
        
        gcs_path = readable_path
    else:
        # ローカルの場合
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # 新形式を優先で試行
        cache_path = CACHE_DIR / readable_path
        cached_data = _read_from_local(cache_path)
        cache_key_used = readable_path
        
        # 新形式がなければ旧形式を試行（後方互換）
        if cached_data is None:
            legacy_path = CACHE_DIR / legacy_key
            cached_data = _read_from_local(legacy_path)
            if cached_data:
                cache_key_used = legacy_key + " (legacy)"
        
        if cached_data and _check_ttl(cached_data, endpoint):
            duration = time.time() - start_time
            logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: HIT ({cache_key_used})")
            return CachedResponse(_unwrap_metadata(cached_data))
    
    # キャッシュミス -> APIリクエスト
    try:
        response = requests.get(url, headers=headers, params=params)
        duration = time.time() - start_time
        backend_name = "GCS" if CACHE_BACKEND == "gcs" else "LOCAL"
        logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: MISS ({backend_name})")
        
        # 成功時のみキャッシュ保存（メタデータ付き）
        if response.status_code == 200:
            data = response.json()
            wrapped_data = _wrap_with_metadata(data)
            
            if CACHE_BACKEND == "gcs":
                _write_to_gcs(readable_path, wrapped_data)
            else:
                cache_path = CACHE_DIR / readable_path
                _write_to_local(cache_path, wrapped_data)
                
        return response
        
    except Exception as e:
        logger.error(f"[API] Request failed: {e}")
        raise
