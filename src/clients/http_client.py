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
    """HTTPレスポンスの抽象化"""

    def __init__(
        self,
        status_code: int,
        json_data: dict,
        ok: bool = True,
        headers: dict = None,
        content: bytes = None,
    ):
        self.status_code = status_code
        self._json_data = json_data
        self.ok = ok
        self.headers = headers or {}
        self.content = content

    def json(self) -> dict:
        return self._json_data

    @property
    def text(self) -> str:
        """テキストとしてレスポンスを返す"""
        if self.content is None:
            return ""
        return self.content.decode("utf-8", errors="replace")

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class CachedResponse(HttpResponse):
    """キャッシュから読み込んだデータを表すレスポンス"""

    def __init__(self, json_data: dict):
        super().__init__(status_code=200, json_data=json_data, ok=True)
        self.from_cache = True


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
        try:
            json_data = response.json() if response.ok else {}
        except ValueError:
            json_data = {}

        return HttpResponse(
            status_code=response.status_code,
            json_data=json_data,
            ok=response.ok,
            headers=dict(response.headers),
            content=response.content,
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
        try:
            json_data = response.json() if response.ok else {}
        except ValueError:
            json_data = {}

        return HttpResponse(
            status_code=response.status_code,
            json_data=json_data,
            ok=response.ok,
            headers=dict(response.headers),
            content=response.content,
        )


_default_http_client = None


def get_http_client() -> HttpClient:
    """デフォルトのHTTPクライアントを取得"""
    global _default_http_client
    if _default_http_client is None:
        _default_http_client = RequestsHttpClient()
    return _default_http_client
