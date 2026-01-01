"""
共通HTTPユーティリティ

Issue #88: APIリクエスト/エラー処理の統一

キャッシュ不要な単純なHTTPリクエスト用のユーティリティ。
タイムアウト・エラー処理を共通化し、安全なリクエストを提供する。

Note:
    キャッシュ機能が必要な場合は CachingHttpClient を使用してください。
"""
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# デフォルトタイムアウト（秒）
DEFAULT_TIMEOUT = 10


def safe_get(
    url: str, 
    headers: Dict[str, str] = None, 
    params: Dict[str, Any] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[requests.Response]:
    """
    安全なGETリクエスト（タイムアウト・エラー処理付き）
    
    Args:
        url: リクエストURL
        headers: リクエストヘッダー
        params: クエリパラメータ
        timeout: タイムアウト秒数
        
    Returns:
        requests.Response または None（エラー時）
    """
    try:
        response = requests.get(
            url, 
            headers=headers or {}, 
            params=params or {},
            timeout=timeout
        )
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        logger.warning(f"Request timeout: {url}")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning(f"Connection error: {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error: {url} - {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request failed: {url} - {e}")
        return None


def safe_get_json(
    url: str, 
    headers: Dict[str, str] = None, 
    params: Dict[str, Any] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[dict]:
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
    url: str, 
    headers: Dict[str, str] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[bytes]:
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
