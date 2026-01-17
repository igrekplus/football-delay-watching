"""
キャッシュ機能付きHTTPクライアント

CacheStoreとHttpClientを組み合わせ、TTL判定を行いながら
APIレスポンスをキャッシュする高レベルクライアント。
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from src.clients.cache_store import CacheStore
from src.clients.http_client import CachedResponse, HttpClient, HttpResponse
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class CachingHttpClient:
    """キャッシュ機能付きHTTPクライアント"""

    def __init__(
        self,
        store: CacheStore,
        http_client: HttpClient,
        ttl_config: dict[str, int | None] = None,
        use_cache: bool = True,
    ):
        """
        Args:
            store: キャッシュストア
            http_client: HTTPクライアント
            ttl_config: エンドポイント別TTL設定（日数）
            use_cache: キャッシュを使用するかどうか
        """
        self.store = store
        self.http_client = http_client
        self.ttl_config = ttl_config or {}
        self.use_cache = use_cache

    def get(
        self,
        url: str,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        **kwargs,
    ) -> HttpResponse:
        """
        キャッシュ機能付きGETリクエスト

        Args:
            url: リクエストURL
            headers: リクエストヘッダー
            params: クエリパラメータ

        Returns:
            HttpResponseオブジェクト（キャッシュヒット時はCachedResponse）
        """
        if params is None:
            params = {}

        start_time = time.time()
        endpoint = self._get_endpoint_from_url(url)

        # TTL=0のエンドポイントはキャッシュしない
        if self.ttl_config.get(endpoint) == 0:
            response = self.http_client.get(url, headers, params)
            duration = time.time() - start_time
            logger.info(
                f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: DISABLED (no-cache endpoint)"
            )
            return response

        # キャッシュ無効時は直接リクエスト
        if not self.use_cache:
            response = self.http_client.get(url, headers, params)
            duration = time.time() - start_time
            logger.info(
                f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: DISABLED"
            )
            return response

        # キャッシュパス生成
        endpoint, cache_path = self.get_cache_path(url, params)

        # キャッシュ読み込み試行
        cached_data = self.store.read(cache_path)

        # 旧形式のキャッシュも試行（後方互換）
        if cached_data is None:
            legacy_path = self._get_legacy_cache_path(url, params, endpoint)
            cached_data = self.store.read(legacy_path)
            if cached_data:
                cache_path = legacy_path + " (legacy)"

        # キャッシュヒット＆TTL有効
        if cached_data and self._check_ttl(cached_data, endpoint):
            duration = time.time() - start_time
            logger.info(
                f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: HIT ({cache_path})"
            )

            # ApiStatsに記録
            api_name = self._identify_api_name(url)
            if api_name:
                ApiStats.record_cache_hit(api_name)

            return CachedResponse(self._unwrap_metadata(cached_data))

        # キャッシュミス → APIリクエスト
        try:
            response = self.http_client.get(url, headers, params)
            duration = time.time() - start_time
            logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: MISS")

            # 成功時のみキャッシュ保存
            if response.ok:
                endpoint, cache_path = self.get_cache_path(url, params)
                wrapped_data = self._wrap_with_metadata(response.json())
                self.store.write(cache_path, wrapped_data)

            return response

        except Exception as e:
            logger.error(f"[API] Request failed: {e}")
            raise

    def delete_cache(self, url: str, params: dict[str, Any]) -> bool:
        """
        特定のキャッシュを削除
        """
        _, cache_path = self.get_cache_path(url, params)
        return self.store.delete(cache_path)

    def _get_endpoint_from_url(self, url: str) -> str:
        """URLからエンドポイント名を抽出"""
        url_suffix = url.split("/")[-1] if "/" in url else "api"
        return "".join(c for c in url_suffix if c.isalnum() or c in ("_", "-"))

    def get_cache_path(self, url: str, params: dict[str, Any]) -> tuple[str, str]:
        """URLとパラメータから可読なキャッシュパスを生成"""
        endpoint = self._get_endpoint_from_url(url)

        # エンドポイント別に可読なパスを生成
        if endpoint == "players" and "id" in params:
            return endpoint, f"players/{params['id']}.json"

        elif endpoint == "lineups" and "fixture" in params:
            return endpoint, f"lineups/fixture_{params['fixture']}.json"

        elif endpoint == "fixtures":
            if "id" in params:
                return endpoint, f"fixtures/id_{params['id']}.json"
            elif "team" in params and "last" in params:
                return (
                    endpoint,
                    f"fixtures/team_{params['team']}_last_{params['last']}.json",
                )
            elif "league" in params and "date" in params:
                return (
                    endpoint,
                    f"fixtures/league_{params['league']}_date_{params['date']}.json",
                )
            elif "league" in params and "season" in params:
                return (
                    endpoint,
                    f"fixtures/league_{params['league']}_season_{params['season']}.json",
                )

        elif endpoint == "headtohead" and "h2h" in params:
            h2h = params["h2h"]
            return endpoint, f"headtohead/{h2h.replace('-', '_vs_')}.json"

        elif endpoint == "statistics" and "team" in params:
            team_id = params["team"]
            season = params.get("season", "unknown")
            league_id = params.get("league", "unknown")
            return (
                endpoint,
                f"statistics/team_{team_id}_season_{season}_league_{league_id}.json",
            )

        elif endpoint == "injuries" and "fixture" in params:
            return endpoint, f"injuries/fixture_{params['fixture']}.json"

        elif endpoint == "squads" and "team" in params:
            return endpoint, f"squads/team_{params['team']}.json"

        # フォールバック: ハッシュベースのパス
        params_str = json.dumps(params, sort_keys=True)
        base_str = f"{url}{params_str}"
        md5_hash = hashlib.md5(base_str.encode("utf-8")).hexdigest()
        return endpoint, f"{endpoint}/{md5_hash}.json"

    def _get_legacy_cache_path(
        self, url: str, params: dict[str, Any], endpoint: str
    ) -> str:
        """旧形式のキャッシュパスを生成（後方互換用）"""
        params_str = json.dumps(params, sort_keys=True)
        base_str = f"{url}{params_str}"
        md5_hash = hashlib.md5(base_str.encode("utf-8")).hexdigest()
        return f"{endpoint}/{md5_hash}.json"

    def _check_ttl(self, cached_data: dict, endpoint: str) -> bool:
        """TTLチェック: キャッシュが有効期限内かどうかを判定"""
        ttl_days = self.ttl_config.get(endpoint)

        # 直近N試合取得（fixtures + last パラメータ）は TTL=2日 (Issue #176)
        # 「最新N試合」は日々変化するため、長期キャッシュは stale になりやすい
        params = cached_data.get("parameters", {})
        if endpoint == "fixtures" and "last" in params:
            ttl_days = 2

        # None = 無期限
        if ttl_days is None:
            return True

        # 0 = キャッシュしない
        if ttl_days == 0:
            return False

        # cached_at が含まれていない場合は旧形式 → 有効とみなす
        cached_at_str = cached_data.get("_cached_at")
        if not cached_at_str:
            logger.debug("Cache missing _cached_at, treating as valid (legacy format)")
            return True

        try:
            cached_at = datetime.fromisoformat(cached_at_str)
            expiry = cached_at + timedelta(days=ttl_days)
            is_valid = datetime.now() < expiry

            if not is_valid:
                logger.info(
                    f"Cache expired: cached_at={cached_at_str}, ttl={ttl_days}d"
                )

            return is_valid
        except Exception as e:
            logger.warning(f"Failed to parse cached_at: {e}")
            return True

    def _wrap_with_metadata(self, data: dict) -> dict:
        """キャッシュデータにメタデータを付与"""
        return {"_cached_at": datetime.now().isoformat(), "_cache_version": 2, **data}

    def _unwrap_metadata(self, cached_data: dict) -> dict:
        """メタデータを除去して元のデータを返す"""
        result = {k: v for k, v in cached_data.items() if not k.startswith("_")}
        return result if result else cached_data

    def _identify_api_name(self, url: str) -> str | None:
        """URLからAPI名を特定"""
        if "api-sports.io" in url:
            return "API-Football"
        return None


def create_caching_client(
    backend: str = None, use_cache: bool = None
) -> CachingHttpClient:
    """
    設定に基づいてCachingHttpClientインスタンスを生成するファクトリ関数

    Args:
        backend: "gcs" または "local"（省略時は設定から取得）
        use_cache: キャッシュ使用フラグ（省略時は設定から取得）

    Returns:
        CachingHttpClientインスタンス
    """
    from settings.cache_config import ENDPOINT_TTL_DAYS, USE_API_CACHE
    from src.clients.cache_store import create_cache_store
    from src.clients.http_client import RequestsHttpClient

    store = create_cache_store(backend)
    http_client = RequestsHttpClient()

    return CachingHttpClient(
        store=store,
        http_client=http_client,
        ttl_config=ENDPOINT_TTL_DAYS,
        use_cache=use_cache if use_cache is not None else USE_API_CACHE,
    )
