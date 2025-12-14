
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

CACHE_DIR = Path("api_cache")

def _get_cache_key(url: str, params: Dict[str, Any]) -> str:
    """URLとパラメータから一意のキャッシュキー（ファイル名）を生成"""
    # パラメータをソートして文字列化し、ハッシュを取る
    params_str = json.dumps(params, sort_keys=True)
    base_str = f"{url}{params_str}"
    md5_hash = hashlib.md5(base_str.encode('utf-8')).hexdigest()
    
    # URLの最後のパスコンポーネントをプレフィックスにする（可読性のため）
    url_suffix = url.split('/')[-1] if '/' in url else "api"
    # ファイル名に使えない文字を除去
    url_suffix = "".join(c for c in url_suffix if c.isalnum() or c in ('_', '-'))
    
    return f"{url_suffix}_{md5_hash}.json"

def get_with_cache(url: str, headers: Dict[str, str], params: Dict[str, Any] = None) -> requests.Response:
    """
    キャッシュ機能付きのGETリクエスト
    
    config.USE_API_CACHE が True の場合:
      - ローカルキャッシュがあればそれを返す
      - なければAPIリクエストを行い、レスポンスJSONを保存して返す
      
    False の場合:
      - 通常の requests.get を実行
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

    # キャッシュディレクトリの準備
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
    cache_filename = _get_cache_key(url, params)
    cache_path = CACHE_DIR / cache_filename
    
    # キャッシュヒット
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Mock Response Objectを作成
            # requests.Response のように振る舞うダミーオブジェクトを返すのが理想だが、
            # 既存コードが .json() しか使っていないなら、
            # .json() メソッドを持つクラスを返せば良い。
            
            class CachedResponse:
                def __init__(self, json_data):
                    self._json_data = json_data
                    self.status_code = 200
                    self.ok = True
                    # text属性なども必要なら追加するが、今回はjson()が主
                    
                @property
                def headers(self):
                    return {}
                    
                def json(self):
                    return self._json_data
                
                def raise_for_status(self):
                    pass

            duration = time.time() - start_time
            logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: HIT ({cache_filename})")
            return CachedResponse(data)
            
        except Exception as e:
            logger.warning(f"Failed to read cache file {cache_filename}: {e}. Fallback to live API.")
    
    # キャッシュミス or 読み込み失敗 -> APIリクエスト
    try:
        response = requests.get(url, headers=headers, params=params)
        duration = time.time() - start_time
        logger.info(f"[API] GET {url} (Duration: {duration:.2f}s) - Cache: MISS")
        
        # 成功時のみキャッシュ保存
        if response.status_code == 200:
            try:
                data = response.json()
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.debug(f"Cache saved to {cache_filename}")
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")
                
        return response
        
    except Exception as e:
        logger.error(f"[API] Request failed: {e}")
        raise
