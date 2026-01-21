"""
HTTPクライアント抽象基底クラスと実装

HTTP通信を抽象化し、テスト時のモック差し替えを可能にする。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class HttpResponse:
    """HTTPレスポンスの抽象化（requests.Response互換）"""

    def __init__(
        self,
        status_code: int,
        content: bytes = None,
        headers: dict = None,
        url: str = "",
        reason: str = "",
        encoding: str = "utf-8",
    ):
        self.status_code = status_code
        self.content = content or b""
        self.headers = headers or {}
        self.url = url
        self.reason = reason
        self.encoding = encoding

    @property
    def ok(self) -> bool:
        """ステータスコードが成功範囲かどうか"""
        return 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        """レスポンスをテキストとして返す"""
        return self.content.decode(self.encoding, errors="replace")

    def json(self) -> dict:
        """レスポンスをJSONとしてパース"""
        import json as json_module

        if not self.content:
            return {}
        try:
            return json_module.loads(self.text)
        except json_module.JSONDecodeError:
            return {}

    def raise_for_status(self):
        """エラーステータスの場合に例外を発生"""
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}: {self.reason}")


class CachedResponse(HttpResponse):
    """キャッシュから読み込んだデータを表すレスポンス"""

    def __init__(self, json_data: dict):
        import json as json_module

        content = json_module.dumps(json_data).encode("utf-8")
        super().__init__(status_code=200, content=content)
        self.from_cache = True
        self._cached_json = json_data

    def json(self) -> dict:
        return self._cached_json


class HttpClient(ABC):
    """HTTPクライアントの抽象基底クラス"""

    @abstractmethod
    def get(
        self,
        url: str,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        """
        GETリクエストを実行

        Args:
            url: リクエストURL
            headers: リクエストヘッダー
            params: クエリパラメータ

        Returns:
            HttpResponseオブジェクト
        """
        pass

    @abstractmethod
    def post(
        self,
        url: str,
        headers: dict[str, str] = None,
        json: dict[str, Any] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        """
        POSTリクエストを実行

        Args:
            url: リクエストURL
            headers: リクエストヘッダー
            json: リクエストボディ(JSON)
            timeout: タイムアウト秒数

        Returns:
            HttpResponseオブジェクト
        """
        pass


class RequestsHttpClient(HttpClient):
    """requestsライブラリを使用するHTTPクライアント"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(
            (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying HTTP request due to {retry_state.outcome.exception()}. "
            f"Attempt {retry_state.attempt_number}."
        ),
    )
    def get(
        self,
        url: str,
        headers: dict[str, str] = None,
        params: dict[str, Any] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        response = requests.get(
            url, headers=headers or {}, params=params or {}, timeout=timeout
        )
        return HttpResponse(
            status_code=response.status_code,
            content=response.content,
            headers=dict(response.headers),
            url=str(response.url),
            reason=response.reason or "",
            encoding=response.encoding or "utf-8",
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(
            (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
        ),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying HTTP request due to {retry_state.outcome.exception()}. "
            f"Attempt {retry_state.attempt_number}."
        ),
    )
    def post(
        self,
        url: str,
        headers: dict[str, str] = None,
        json: dict[str, Any] = None,
        timeout: int = 30,
    ) -> HttpResponse:
        response = requests.post(url, headers=headers or {}, json=json, timeout=timeout)
        return HttpResponse(
            status_code=response.status_code,
            content=response.content,
            headers=dict(response.headers),
            url=str(response.url),
            reason=response.reason or "",
            encoding=response.encoding or "utf-8",
        )


_default_http_client = None


def get_http_client() -> HttpClient:
    """デフォルトのHTTPクライアントを取得"""
    global _default_http_client
    if _default_http_client is None:
        _default_http_client = RequestsHttpClient()
    return _default_http_client
