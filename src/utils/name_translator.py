"""
Name Translator - 選手名を英語からカタカナに変換するユーティリティ

HTML生成後に選手名を一括変換し、GCSにキャッシュする。
"""

import json
import logging
import hashlib
from typing import List, Dict, Optional

from src.clients.gemini_rest_client import GeminiRestClient
from src.clients.cache_store import CacheStore, create_cache_store
from src.utils.api_stats import ApiStats
from config import config

logger = logging.getLogger(__name__)


class NameTranslator:
    """選手名を英語→カタカナに変換するユーティリティ"""
    
    CACHE_PREFIX = "name_translation"
    
    def __init__(self, cache_store: CacheStore = None, use_mock: bool = None):
        """
        Args:
            cache_store: キャッシュストア（省略時は自動生成）
            use_mock: モックモード（省略時はconfig.USE_MOCK_DATA）
        """
        self.gemini = GeminiRestClient()
        self.cache_store = cache_store or create_cache_store()
        self.use_mock = use_mock if use_mock is not None else config.USE_MOCK_DATA
    
    def translate_names_in_html(self, html: str, player_names: List[str]) -> str:
        """
        HTML内の選手名をカタカナに置換
        
        Args:
            html: HTMLコンテンツ
            player_names: 変換対象の選手名リスト（英語）
            
        Returns:
            選手名がカタカナに置換されたHTML
        """
        if not player_names:
            return html
        
        # 重複を除去してソート（長い名前から置換して部分一致を防ぐ）
        unique_names = list(set(player_names))
        unique_names.sort(key=len, reverse=True)
        
        # 翻訳マッピングを取得
        translations = self._get_translations(unique_names)
        
        # HTML内で置換
        result = html
        for english_name, katakana_name in translations.items():
            if katakana_name and katakana_name != english_name:
                result = result.replace(english_name, katakana_name)
        
        return result
    
    def _get_translations(self, names: List[str]) -> Dict[str, str]:
        """
        選手名の翻訳(Full)を取得（キャッシュ優先）
        Compatibility wrapper for existing code
        """
        translations = {}
        names_to_translate = []
        
        # キャッシュから取得
        for name in names:
            cached = self._read_cache(name)
            if cached:
                translations[name] = cached["full"]
                # logger.debug(f"[NAME_TRANSLATION] Cache HIT: {name} -> {cached['full']}")
            else:
                names_to_translate.append(name)
        
        # 未翻訳の名前をGeminiで変換
        if names_to_translate:
            logger.info(f"[NAME_TRANSLATION] Cache MISS: {len(names_to_translate)} names to translate")
            new_translations = self._batch_translate(names_to_translate)
            
            # キャッシュに保存
            for name, trans_data in new_translations.items():
                self._write_cache(name, trans_data)
                translations[name] = trans_data["full"]
        
        return translations
    
    def _batch_translate(self, names: List[str]) -> Dict[str, str]:
        """
        複数の選手名を一括変換（1回のAPIコール）
        
        Args:
            names: 変換対象の選手名リスト
            
        Returns:
            {英語名: カタカナ名} のマッピング
        """
        if self.use_mock:
            # モックモードではそのまま返す
            return {name: f"[MOCK]{name}" for name in names}
        
        if not names:
            return {}
        
        # バッチサイズを制限（プロンプトが長すぎるとエラーになる可能性）
        batch_size = 50
        all_translations = {}
        
        for i in range(0, len(names), batch_size):
            batch = names[i:i + batch_size]
            batch_translations = self._translate_batch(batch)
            all_translations.update(batch_translations)
        
        return all_translations
    
    def _translate_batch(self, names: List[str]) -> Dict[str, str]:
        """単一バッチの変換"""
        from settings.gemini_prompts import build_prompt
        
        names_list = "\n".join(f"- {name}" for name in names)
        prompt = build_prompt("name_translation", names_list=names_list)
        
        try:
            response = self.gemini.generate_content(prompt)
            ApiStats.record_call("Gemini API (Translation)")
            
            # JSONパース（Geminiの出力から抽出）
            # 時々マークダウンコードブロックで返ってくることがある
            json_str = response.strip()
            if json_str.startswith("```"):
                # コードブロックを除去
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])
            
            translations = json.loads(json_str)
            logger.info(f"[NAME_TRANSLATION] Translated {len(translations)} names via Gemini")
            
            # 形式の正規化（古い形式 {name: full} が返ってきた場合の対策）
            normalized = {}
            for k, v in translations.items():
                if isinstance(v, str):
                    normalized[k] = {"full": v, "short": v}
                elif isinstance(v, dict):
                    normalized[k] = v
                    # shortがない場合はfullを使う
                    if "short" not in normalized[k]:
                        normalized[k]["short"] = normalized[k].get("full", k)
            
            return normalized
            
        except json.JSONDecodeError as e:
            logger.error(f"[NAME_TRANSLATION] Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {response}")
            return {name: {"full": name, "short": name} for name in names}
            
        except Exception as e:
            logger.error(f"[NAME_TRANSLATION] Translation error: {e}")
            return {name: {"full": name, "short": name} for name in names}
    
    def _get_cache_path(self, name: str) -> str:
        """キャッシュパスを生成"""
        # 名前をハッシュ化してパスに使用（ファイル名に使えない文字対策）
        name_hash = hashlib.md5(name.encode()).hexdigest()[:16]
        return f"{self.CACHE_PREFIX}/{name_hash}.json"
    
    def _read_cache(self, name: str) -> Optional[dict]:
        """
        キャッシュから翻訳を読み込む
        Returns: {"full": "...", "short": "..."} or None
        """
        try:
            cache_path = self._get_cache_path(name)
            data = self.cache_store.read(cache_path)
            if data and data.get("original") == name:
                # 旧形式: shortがない場合はキャッシュミス扱いにして再取得を促す
                if "short" not in data:
                    return None
                # 新形式
                if "full" in data and "short" in data:
                    return {"full": data["full"], "short": data["short"]}
        except Exception as e:
            logger.debug(f"[NAME_TRANSLATION] Cache read error: {e}")
        return None
    
    def _write_cache(self, name: str, translation: dict) -> None:
        """翻訳をキャッシュに書き込む"""
        try:
            cache_path = self._get_cache_path(name)
            
            # 既存データがあれば読み込んでマージ（既存のfullを尊重）
            existing = self.cache_store.read(cache_path)
            full_name = translation.get("full")
            if existing and existing.get("original") == name:
                if "katakana" in existing and not full_name:
                    full_name = existing["katakana"]
                elif "full" in existing and not full_name:
                    full_name = existing["full"]
            
            data = {
                "original": name,
                "full": full_name or name,
                "short": translation.get("short") or full_name or name,
                # 下位互換用
                "katakana": full_name or name
            }
            self.cache_store.write(cache_path, data)
        except Exception as e:
            logger.warning(f"[NAME_TRANSLATION] Cache write error: {e}")

    def get_short_names(self, names: List[str]) -> Dict[str, str]:
        """
        選手名の短縮名マッピングを取得
        """
        if not names:
            return {}
            
        # 翻訳処理（キャッシュ確認含む）を実行
        # _get_translations は内部でキャッシュ確認とAPIコールを行う
        # 返り値は現状 {eng: full_katakana} になっているので、
        # 内部メソッドを修正するか、キャッシュを直接読む必要がある
        
        # ここでは _get_translations を修正するのではなく、
        # 必要な翻訳を確実に行わせた上で、キャッシュから短縮名を引くアプローチを取る
        
        # 1. まず翻訳を確保（未キャッシュ分はAPIコール）
        self._ensure_translations(names)
        
        # 2. キャッシュから短縮名を収集
        result = {}
        for name in names:
            cached = self._read_cache(name)
            if cached:
                result[name] = cached["short"]
            else:
                result[name] = name # フォールバック
                
        return result

    def _ensure_translations(self, names: List[str]):
        """指定された名前の翻訳がキャッシュにあることを保証する"""
        names_to_translate = []
        for name in names:
            if not self._read_cache(name):
                names_to_translate.append(name)
        
        if names_to_translate:
            logger.info(f"[NAME_TRANSLATION] Translating {len(names_to_translate)} names for short name retrieval")
            new_translations = self._batch_translate(names_to_translate)
            for name, trans_data in new_translations.items():
                # trans_data is {"full": ..., "short": ...}
                self._write_cache(name, trans_data)
