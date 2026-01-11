"""
YouTube Data API クライアント

YouTube Data API v3とのやり取りを一元化し、キャッシュ管理も担当する。
ServiceはこのClientを通じてYouTube検索機能を使用する。
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable

import requests

from config import config
from src.clients.cache_store import CacheStore, create_cache_store
from settings.cache_config import ENDPOINT_TTL_DAYS, USE_YOUTUBE_CACHE
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class YouTubeSearchClient:
    """YouTube Data API v3 クライアント"""
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    def __init__(
        self,
        api_key: str = None,
        http_get: Optional[Callable] = None,
        cache_enabled: Optional[bool] = None,
        cache_store: CacheStore = None,
    ):
        """
        Args:
            api_key: YouTube API Key（省略時は環境変数 or config）
            http_get: HTTPリクエスト関数（テスト用DI）
            cache_enabled: キャッシュ有効化フラグ
            cache_store: キャッシュストア（省略時は自動生成）
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or config.GOOGLE_API_KEY
        self._http_get = http_get or requests.get
        self.use_youtube_cache = USE_YOUTUBE_CACHE if cache_enabled is None else cache_enabled
        self.cache_store = cache_store or create_cache_store()
        
        # API呼び出し/キャッシュヒットカウンター
        self.api_call_count = 0
        self.cache_hit_count = 0
    
    def _get_cache_path(
        self, 
        query: str, 
        channel_id: Optional[str],
        published_after: Optional[datetime],
        published_before: Optional[datetime],
        relevance_language: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> str:
        """検索条件からキャッシュパス（キー）を生成"""
        key_parts = [
            query,
            channel_id or "",
            published_after.strftime("%Y%m%d") if published_after else "",
            published_before.strftime("%Y%m%d") if published_before else "",
            relevance_language or "",
            region_code or "",
        ]
        key_str = "|".join(key_parts)
        query_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"youtube/{query_hash}.json"
    
    def _read_cache(self, cache_path: str) -> Optional[List[Dict]]:
        """キャッシュから読み込み（TTLチェック付き）"""
        if not self.use_youtube_cache:
            return None
        
        try:
            data = self.cache_store.read(cache_path)
            if not data:
                return None
            
            # TTLチェック
            cached_at_str = data.get("cached_at")
            ttl_days = ENDPOINT_TTL_DAYS.get("youtube", 7)
            
            if cached_at_str:
                cached_at = datetime.fromisoformat(cached_at_str)
                if datetime.now() - cached_at < timedelta(days=ttl_days):
                    logger.info(f"YouTube cache HIT: {cache_path}")
                    self.cache_hit_count += 1
                    ApiStats.record_cache_hit("YouTube Data API")
                    return data.get("results", [])
                else:
                    logger.debug(f"YouTube cache expired: {cache_path}")
            else:
                # タイムスタンプがない場合は古い形式か無期限扱い
                logger.info(f"YouTube cache HIT (no timestamp): {cache_path}")
                self.cache_hit_count += 1
                ApiStats.record_cache_hit("YouTube Data API")
                return data.get("results", [])
                
        except Exception as e:
            logger.warning(f"Failed to read YouTube cache {cache_path}: {e}")
        
        return None
    
    def _write_cache(self, cache_path: str, results: List[Dict]):
        """キャッシュに書き込み"""
        if not self.use_youtube_cache or not results:
            return
        
        try:
            data = {
                "cached_at": datetime.now().isoformat(),
                "results": results,
            }
            self.cache_store.write(cache_path, data)
            logger.debug(f"YouTube cache saved: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to write YouTube cache {cache_path}: {e}")
    
    def search(
        self,
        query: str,
        published_after: Optional[datetime] = None,
        published_before: Optional[datetime] = None,
        max_results: int = 10,
        relevance_language: Optional[str] = None,
        region_code: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        YouTube検索を実行（1週間キャッシュ付き）
        
        Args:
            query: 検索クエリ
            published_after: 公開日（以降）
            published_before: 公開日（以前）
            max_results: 取得件数
            relevance_language: 結果の言語優先度（ISO 639-1、例: "ja"）
            region_code: 地域コード
            channel_id: チャンネルID（指定時はそのチャンネルのみ検索）
            
        Returns:
            動画情報のリスト
        """
        # キャッシュチェック
        cache_path = self._get_cache_path(
            query,
            channel_id,
            published_after,
            published_before,
            relevance_language,
            region_code,
        )
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached[:max_results]
        
        # API呼び出し
        try:
            url = f"{self.API_BASE}/search"
            params = {
                "key": self.api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "maxResults": max_results,
                "order": "relevance",
            }
            
            if published_after:
                params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            if published_before:
                params["publishedBefore"] = published_before.strftime("%Y-%m-%dT%H:%M:%SZ")
            
            if relevance_language:
                params["relevanceLanguage"] = relevance_language
            if region_code:
                params["regionCode"] = region_code
            if channel_id:
                params["channelId"] = channel_id
            
            response = self._http_get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for i, item in enumerate(data.get("items", [])):
                    video_id = item["id"].get("videoId")
                    if video_id:
                        results.append({
                            "video_id": video_id,
                            "title": item["snippet"]["title"],
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "channel_id": item["snippet"]["channelId"],
                            "channel_name": item["snippet"]["channelTitle"],
                            "thumbnail_url": item["snippet"]["thumbnails"]["medium"]["url"],
                            "published_at": item["snippet"]["publishedAt"],
                            "description": item["snippet"].get("description", ""),
                            "original_index": i,  # relevance順を保持
                        })
                
                # キャッシュ保存
                self._write_cache(cache_path, results)
                self.api_call_count += 1
                ApiStats.record_call("YouTube Data API")
                logger.info(f"YouTube API: '{query}' -> {len(results)} results (API calls: {self.api_call_count})")
                
                return results
            else:
                logger.warning(f"YouTube search failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
        
        return []
    
    def get_stats(self) -> Dict[str, int]:
        """API呼び出しとキャッシュヒットの統計を返す"""
        return {
            "api_calls": self.api_call_count,
            "cache_hits": self.cache_hit_count,
        }
    
    def reset_stats(self):
        """統計をリセット"""
        self.api_call_count = 0
        self.cache_hit_count = 0
