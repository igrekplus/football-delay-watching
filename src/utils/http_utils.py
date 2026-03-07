"""
共通HTTPユーティリティ

Issue #88: APIリクエスト/エラー処理の統一

キャッシュ不要な単純なHTTPリクエスト用のユーティリティ。
タイムアウト・エラー処理を共通化し、安全なリクエストを提供する。

Note:
    キャッシュ機能が必要な場合は CachingHttpClient を使用してください。
"""

import logging
from typing import Any

from src.clients.http_client import get_http_client

logger = logging.getLogger(__name__)

# デフォルトタイムアウト（秒）
DEFAULT_TIMEOUT = 10


def safe_get(
    url: str,
    headers: dict[str, str] = None,
    params: dict[str, Any] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Any | None:
    """
    安全なGETリクエスト（タイムアウト・リトライ処理付き）
    """
    try:
        http_client = get_http_client()
        response = http_client.get(
            url, headers=headers or {}, params=params or {}, timeout=timeout
        )
        if response.ok:
            return response
        else:
            logger.warning(f"HTTP error: {url} - {response.status_code}")
            return None
    except Exception as e:
        logger.warning(f"Request failed: {url} - {e}")
        return None


def safe_get_json(
    url: str,
    headers: dict[str, str] = None,
    params: dict[str, Any] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict | None:
    """
    安全なGETリクエスト（JSON返却）

    Args:
        url: リクエストURL
        headers: リクエストヘッダー
        params: クエリパラメータ
        timeout: タイムアウト秒数

    Returns:
        JSONデータ（dict）または None（エラー時）
    """
    response = safe_get(url, headers, params, timeout)
    if response:
        try:
            return response.json()
        except Exception as e:
            logger.warning(f"JSON parse failed: {url} - {e}")
    return None


def safe_get_bytes(
    url: str, headers: dict[str, str] = None, timeout: int = DEFAULT_TIMEOUT
) -> bytes | None:
    """
    安全なGETリクエスト（バイナリ返却）

    画像などのバイナリコンテンツ取得用。

    Args:
        url: リクエストURL
        headers: リクエストヘッダー
        timeout: タイムアウト秒数

    Returns:
        バイナリデータまたは None（エラー時）
    """
    response = safe_get(url, headers, timeout=timeout)
    if response:
        return response.content
    return None
