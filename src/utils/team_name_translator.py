import hashlib
import json
import logging

from config import config
from src.clients.cache_store import CacheStore, create_cache_store
from src.clients.gemini_rest_client import GeminiRestClient
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class TeamNameTranslator:
    """チーム名を英語→カタカナに翻訳するユーティリティ"""

    CACHE_PREFIX = "team_translation"

    def __init__(self, cache_store: CacheStore = None, use_mock: bool = None):
        """
        Args:
            cache_store: キャッシュストア（省略時は自動生成）
            use_mock: モックモード（省略時はconfig.USE_MOCK_DATA）
        """
        self.gemini = GeminiRestClient()
        self.cache_store = cache_store or create_cache_store()
        self.use_mock = use_mock if use_mock is not None else config.USE_MOCK_DATA

    def get_katakana_keywords(self, team_name: str) -> list[str]:
        """
        チーム名からフィルタリング用のカタカナキーワードを取得

        Args:
            team_name: 英語のチーム名

        Returns:
            カタカナキーワードのリスト
        """
        if not team_name:
            return []

        katakana = self._get_translation(team_name)
        if not katakana:
            return []

        keywords = [katakana]
        # 中黒で分割して各パーツもキーワードとして追加（例: マンチェスター・シティ -> [マンチェスター, シティ]）
        parts = [p.strip() for p in katakana.split("・") if len(p.strip()) >= 2]
        keywords.extend(parts)

        # 重複除去して、長い順にソート（マッチングの精度向上のため）
        unique_keywords = list(set(keywords))
        unique_keywords.sort(key=len, reverse=True)

        return unique_keywords

    def _get_translation(self, team_name: str) -> str | None:
        """キャッシュ優先で翻訳を取得"""
        cached = self._read_cache(team_name)
        if cached:
            # logger.debug(f"[TEAM_TRANSLATION] Cache HIT: {team_name} -> {cached}")
            return cached

        logger.info(f"[TEAM_TRANSLATION] Cache MISS: Translating team '{team_name}'")
        translated = self._translate_team(team_name)

        if translated:
            self._write_cache(team_name, translated)

        return translated

    def _translate_team(self, team_name: str) -> str | None:
        """Gemini APIを使用してチーム名を翻訳"""
        if self.use_mock:
            return f"[MOCK]{team_name}"

        from settings.gemini_prompts import build_prompt

        prompt = build_prompt("team_name_translation", team_name=team_name)

        try:
            response = self.gemini.generate_content(prompt)
            ApiStats.record_call("Gemini API (Team Translation)")

            json_str = response.strip()
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])

            translations = json.loads(json_str)
            # 形式: {"Team Name": "カタカナ"}
            katakana = list(translations.values())[0] if translations else None

            if katakana:
                logger.info(
                    f"[TEAM_TRANSLATION] Translated '{team_name}' to '{katakana}'"
                )
            return katakana

        except Exception as e:
            logger.error(f"[TEAM_TRANSLATION] Translation error for '{team_name}': {e}")
            return None

    def _get_cache_path(self, team_name: str) -> str:
        """キャッシュパスを生成"""
        name_hash = hashlib.md5(team_name.encode()).hexdigest()[:16]
        return f"{self.CACHE_PREFIX}/{name_hash}.json"

    def _read_cache(self, team_name: str) -> str | None:
        """キャッシュ読み込み"""
        try:
            cache_path = self._get_cache_path(team_name)
            data = self.cache_store.read(cache_path)
            if data and data.get("original") == team_name:
                return data.get("katakana")
        except Exception:
            pass
        return None

    def _write_cache(self, team_name: str, katakana: str) -> None:
        """キャッシュ書き込み"""
        try:
            cache_path = self._get_cache_path(team_name)
            data = {
                "original": team_name,
                "katakana": katakana,
            }
            self.cache_store.write(cache_path, data)
        except Exception as e:
            logger.warning(f"[TEAM_TRANSLATION] Cache write error: {e}")
