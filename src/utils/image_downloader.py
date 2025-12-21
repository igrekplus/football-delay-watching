"""
選手画像ダウンロードユーティリティ

API-Footballから取得した選手画像URLをローカルにダウンロードし、
メール添付やPDF埋め込みに対応できるようにする。
"""

import os
import hashlib
import logging
from typing import Dict, Optional
import requests

logger = logging.getLogger(__name__)


def download_player_images(
    player_photos: Dict[str, str],
    output_dir: str,
    match_id: str
) -> Dict[str, str]:
    """
    選手画像をダウンロードしてローカルパスを返す
    
    Args:
        player_photos: {選手名: 画像URL} の辞書
        output_dir: 画像保存先ディレクトリ（例: reports/images）
        match_id: 試合ID（ファイル名のプレフィックス用）
    
    Returns:
        {選手名: ローカルファイルパス} の辞書
    """
    if not player_photos:
        return {}
    
    # 画像保存ディレクトリを作成
    images_dir = os.path.join(output_dir, "images", "players")
    os.makedirs(images_dir, exist_ok=True)
    
    local_paths = {}
    
    for player_name, url in player_photos.items():
        if not url:
            continue
        
        try:
            # ファイル名を生成（URLハッシュ + 選手名の一部）
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            safe_name = "".join(c for c in player_name if c.isalnum() or c in " -_")[:20]
            filename = f"{match_id}_{url_hash}_{safe_name}.png"
            filepath = os.path.join(images_dir, filename)
            
            # 既にダウンロード済みの場合はスキップ
            if os.path.exists(filepath):
                local_paths[player_name] = filepath
                continue
            
            # 画像をダウンロード
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with open(filepath, "wb") as f:
                f.write(response.content)
            
            local_paths[player_name] = filepath
            logger.debug(f"Downloaded player image: {player_name} -> {filepath}")
            
        except Exception as e:
            logger.warning(f"Failed to download image for {player_name}: {e}")
            continue
    
    logger.info(f"Downloaded {len(local_paths)}/{len(player_photos)} player images")
    return local_paths
