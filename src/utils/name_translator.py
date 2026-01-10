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
        選手名の翻訳を取得（キャッシュ優先）
        
        Returns:
            {英語名: カタカナ名} のマッピング
        """
        translations = {}
        names_to_translate = []
        
        # キャッシュから取得
        for name in names:
            cached = self._read_cache(name)
            if cached:
                translations[name] = cached
                logger.debug(f"[NAME_TRANSLATION] Cache HIT: {name} -> {cached}")
            else:
                names_to_translate.append(name)
        
        # 未翻訳の名前をGeminiで変換
        if names_to_translate:
            logger.info(f"[NAME_TRANSLATION] Cache MISS: {len(names_to_translate)} names to translate")
            new_translations = self._batch_translate(names_to_translate)
            
            # キャッシュに保存
            for name, katakana in new_translations.items():
                self._write_cache(name, katakana)
                translations[name] = katakana
        
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
        names_list = "\n".join(f"- {name}" for name in names)
        
        prompt = f"""以下のサッカー選手名を日本語（カタカナ）に変換してください。

ルール:
1. 一般的に使われる表記を優先（例: Mohamed Salah → モハメド・サラー）
2. 姓名の間は中黒（・）で区切る
3. 不明な場合はローマ字読みをカタカナ化

JSON形式で出力してください（余計な説明は不要）:
{{"選手名（元）": "カタカナ", ...}}

選手名リスト:
{names_list}
"""
        
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
            return translations
            
        except json.JSONDecodeError as e:
            logger.error(f"[NAME_TRANSLATION] Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {response}")
            # パース失敗時は元の名前を返す
            return {name: name for name in names}
        except Exception as e:
            logger.error(f"[NAME_TRANSLATION] Translation error: {e}")
            return {name: name for name in names}
    
    def _get_cache_path(self, name: str) -> str:
        """キャッシュパスを生成"""
        # 名前をハッシュ化してパスに使用（ファイル名に使えない文字対策）
        name_hash = hashlib.md5(name.encode()).hexdigest()[:16]
        return f"{self.CACHE_PREFIX}/{name_hash}.json"
    
    def _read_cache(self, name: str) -> Optional[str]:
        """キャッシュから翻訳を読み込む"""
        try:
            cache_path = self._get_cache_path(name)
            data = self.cache_store.read(cache_path)
            if data and data.get("original") == name:
                return data.get("katakana")
        except Exception as e:
            logger.debug(f"[NAME_TRANSLATION] Cache read error: {e}")
        return None
    
    def _write_cache(self, name: str, katakana: str) -> None:
        """翻訳をキャッシュに書き込む"""
        try:
            cache_path = self._get_cache_path(name)
            data = {
                "original": name,
                "katakana": katakana
            }
            self.cache_store.write(cache_path, data)
        except Exception as e:
            logger.warning(f"[NAME_TRANSLATION] Cache write error: {e}")
