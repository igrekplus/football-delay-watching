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

logger = logging.getLogger(__name__)

# YouTube検索結果のキャッシュ設定
YOUTUBE_CACHE_DIR = Path("api_cache/youtube")
YOUTUBE_CACHE_TTL_HOURS = 168  # キャッシュ有効期限（1週間）


class YouTubeSearchClient:
    """YouTube Data API v3 クライアント"""
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    def __init__(
        self,
        api_key: str = None,
        http_get: Optional[Callable] = None,
        cache_enabled: Optional[bool] = None,
    ):
        """
        Args:
            api_key: YouTube API Key（省略時は環境変数 or config）
            http_get: HTTPリクエスト関数（テスト用DI）
            cache_enabled: キャッシュ有効化フラグ
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or config.GOOGLE_API_KEY
        self._http_get = http_get or requests.get
        self._cache_enabled = config.USE_API_CACHE if cache_enabled is None else cache_enabled
        
        # API呼び出し/キャッシュヒットカウンター
        self.api_call_count = 0
        self.cache_hit_count = 0
    
    def _get_cache_key(
        self, 
        query: str, 
        channel_id: Optional[str],
        published_after: Optional[datetime],
        published_before: Optional[datetime],
        relevance_language: Optional[str] = None,
        region_code: Optional[str] = None,
    ) -> str:
        """検索条件からキャッシュキーを生成"""
        key_parts = [
            query,
            channel_id or "",
            published_after.strftime("%Y%m%d") if published_after else "",
            published_before.strftime("%Y%m%d") if published_before else "",
            relevance_language or "",
            region_code or "",
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _read_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """キャッシュから読み込み（TTLチェック付き）"""
        if not self._cache_enabled:
            return None
        
        cache_file = YOUTUBE_CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # TTLチェック
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_at > timedelta(hours=YOUTUBE_CACHE_TTL_HOURS):
                logger.debug(f"Cache expired: {cache_key}")
                return None
            
            logger.info(f"YouTube cache HIT: {cache_key[:8]}...")
            self.cache_hit_count += 1
            return data.get("results", [])
        except Exception as e:
            logger.warning(f"Failed to read YouTube cache: {e}")
            return None
    
    def _write_cache(self, cache_key: str, results: List[Dict]):
        """キャッシュに書き込み"""
        if not self._cache_enabled:
            return
        
        try:
            YOUTUBE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = YOUTUBE_CACHE_DIR / f"{cache_key}.json"
            
            data = {
                "cached_at": datetime.now().isoformat(),
                "results": results,
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"YouTube cache saved: {cache_key[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to write YouTube cache: {e}")
    
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
        cache_key = self._get_cache_key(
            query,
            channel_id,
            published_after,
            published_before,
            relevance_language,
            region_code,
        )
        cached = self._read_cache(cache_key)
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
                self._write_cache(cache_key, results)
                self.api_call_count += 1
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
