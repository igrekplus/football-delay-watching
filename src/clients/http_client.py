"""
HTTPクライアント抽象基底クラスと実装

HTTP通信を抽象化し、テスト時のモック差し替えを可能にする。
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)


class HttpResponse:
    """HTTPレスポンスの抽象化"""
    
    def __init__(self, status_code: int, json_data: dict, ok: bool = True):
        self.status_code = status_code
        self._json_data = json_data
        self.ok = ok
        self.headers = {}
    
    def json(self) -> dict:
        return self._json_data
    
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
        headers: Dict[str, str] = None, 
        params: Dict[str, Any] = None
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


class RequestsHttpClient(HttpClient):
    """requestsライブラリを使用するHTTPクライアント"""
    
    def get(
        self, 
        url: str, 
        headers: Dict[str, str] = None, 
        params: Dict[str, Any] = None
    ) -> HttpResponse:
        response = requests.get(url, headers=headers or {}, params=params or {})
        return HttpResponse(
            status_code=response.status_code,
            json_data=response.json() if response.ok else {},
            ok=response.ok
        )
