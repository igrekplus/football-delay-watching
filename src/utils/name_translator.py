"""
Name Translator - 選手名を英語からカタカナに変換するユーティリティ

HTML生成後に選手名を一括変換し、GCSにキャッシュする。
"""

import hashlib
import html
import json
import logging
import re
import unicodedata

from config import config
from src.clients.cache_store import CacheStore, create_cache_store
from src.clients.llm_client import LLMClient
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class NameTranslator:
    """選手名を英語→カタカナに変換するユーティリティ"""

    CACHE_PREFIX = "name_translation"
    MOCK_PREFIX = "[MOCK]"

    def __init__(self, cache_store: CacheStore = None, use_mock: bool = None):
        """
        Args:
            cache_store: キャッシュストア（省略時は自動生成）
            use_mock: モックモード（省略時はconfig.USE_MOCK_DATA）
        """
        self.cache_store = cache_store or create_cache_store()
        self.use_mock = use_mock if use_mock is not None else config.USE_MOCK_DATA
        self.llm = LLMClient(use_mock=self.use_mock)

    def translate_names_in_html(self, html: str, player_names: list[str]) -> str:
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
                for source_variant in self._build_html_name_variants(english_name):
                    result = result.replace(source_variant, katakana_name)

        # フルネームで置換しきれない「姓のみ」の参照も、対象が一意なら補完する
        for alias, katakana_name in self._build_unique_name_aliases(
            unique_names, translations
        ).items():
            if katakana_name and katakana_name != alias:
                result = self._replace_alias_token(result, alias, katakana_name)

        return result

    def _get_translations(self, names: list[str]) -> dict[str, str]:
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
            logger.info(
                f"[NAME_TRANSLATION] Cache MISS: {len(names_to_translate)} names to translate"
            )
            new_translations = self._align_translations_to_requested_names(
                names_to_translate, self._batch_translate(names_to_translate)
            )

            # キャッシュに保存
            for name, trans_data in new_translations.items():
                self._write_cache(name, trans_data)
                translations[name] = trans_data["full"]

        return translations

    def _batch_translate(self, names: list[str]) -> dict[str, dict[str, str]]:
        """
        複数の選手名を一括変換（1回のAPIコール）

        Args:
            names: 変換対象の選手名リスト

        Returns:
            {英語名: カタカナ名} のマッピング
        """
        if self.use_mock:
            # モックモードでも「full」と「short」を持つ辞書を返す
            return {
                name: {"full": f"[MOCK]{name}", "short": f"{name}"} for name in names
            }

        if not names:
            return {}

        # バッチサイズを制限（プロンプトが長すぎるとエラーになる可能性）
        batch_size = 50
        all_translations = {}

        for i in range(0, len(names), batch_size):
            batch = names[i : i + batch_size]
            batch_translations = self._translate_batch(batch)
            all_translations.update(batch_translations)

        return all_translations

    def _translate_batch(self, names: list[str]) -> dict[str, dict[str, str]]:
        """単一バッチの変換"""
        from settings.gemini_prompts import build_prompt

        names_list = "\n".join(f"- {name}" for name in names)
        prompt = build_prompt("name_translation", names_list=names_list)

        try:
            response = self.llm.generate_content(prompt, prompt_type="name_translation")
            ApiStats.record_call("LLM (Name Translation)")

            # JSONパース（Geminiの出力から抽出）
            # 時々マークダウンコードブロックで返ってくることがある
            json_str = response.strip()
            if json_str.startswith("```"):
                # コードブロックを除去
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1])

            translations = json.loads(json_str)
            logger.info(
                f"[NAME_TRANSLATION] Translated {len(translations)} names via LLM"
            )

            return self._align_translations_to_requested_names(names, translations)

        except json.JSONDecodeError as e:
            logger.error(f"[NAME_TRANSLATION] Failed to parse LLM response: {e}")
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

    def _read_cache(self, name: str) -> dict | None:
        """
        キャッシュから翻訳を読み込む
        Returns: {"full": "...", "short": "..."} or None
        """
        try:
            cache_path = self._get_cache_path(name)
            data = self.cache_store.read(cache_path)
            if data and data.get("original") == name:
                full = str(data.get("full") or data.get("katakana") or "").strip()
                short = str(data.get("short") or "").strip()

                # 旧形式や空文字キャッシュはキャッシュミス扱いにして再取得を促す
                if not full or not short:
                    logger.info(
                        f"[NAME_TRANSLATION] Incomplete cache detected and ignored: {name}"
                    )
                    self.cache_store.delete(cache_path)
                    return None

                # 新形式
                if "full" in data and "short" in data:
                    if not self.use_mock and self._is_mock_contaminated(data):
                        logger.warning(
                            f"[NAME_TRANSLATION] Invalid mock cache detected and ignored: {name}"
                        )
                        self.cache_store.delete(cache_path)
                        return None
                    return {"full": full, "short": short}
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
                if (
                    "katakana" in existing
                    and not full_name
                    and (
                        self.use_mock
                        or not self._is_mock_value(str(existing.get("katakana", "")))
                    )
                ):
                    full_name = existing["katakana"]
                elif (
                    "full" in existing
                    and not full_name
                    and (
                        self.use_mock
                        or not self._is_mock_value(str(existing.get("full", "")))
                    )
                ):
                    full_name = existing["full"]

            data = {
                "original": name,
                "full": full_name or name,
                "short": translation.get("short") or full_name or name,
                # 下位互換用
                "katakana": full_name or name,
            }
            self.cache_store.write(cache_path, data)
        except Exception as e:
            logger.warning(f"[NAME_TRANSLATION] Cache write error: {e}")

    def get_short_names(self, names: list[str]) -> dict[str, str]:
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
                result[name] = name  # フォールバック

        return result

    def _ensure_translations(self, names: list[str]):
        """指定された名前の翻訳がキャッシュにあることを保証する"""
        names_to_translate = []
        for name in names:
            if not self._read_cache(name):
                names_to_translate.append(name)

        if names_to_translate:
            logger.info(
                f"[NAME_TRANSLATION] Translating {len(names_to_translate)} names for short name retrieval"
            )
            new_translations = self._align_translations_to_requested_names(
                names_to_translate, self._batch_translate(names_to_translate)
            )
            for name, trans_data in new_translations.items():
                # trans_data is {"full": ..., "short": ...}
                self._write_cache(name, trans_data)

    def _is_mock_value(self, value: str) -> bool:
        return value.startswith(self.MOCK_PREFIX)

    def _is_mock_contaminated(self, data: dict) -> bool:
        full = str(data.get("full", ""))
        katakana = str(data.get("katakana", ""))
        short = str(data.get("short", ""))
        return (
            self._is_mock_value(full)
            or self._is_mock_value(katakana)
            or self._is_mock_value(short)
        )

    def _normalize_name_key(self, value: str) -> str:
        """アクセントや記号差を吸収した比較用キーを返す"""
        normalized = unicodedata.normalize("NFKD", value)
        without_marks = "".join(
            ch for ch in normalized if not unicodedata.combining(ch)
        )
        simplified = (
            without_marks.casefold()
            .replace("’", "'")
            .replace("`", "'")
            .replace("・", ".")
        )
        compact = "".join(ch for ch in simplified if ch.isalnum())
        return compact or simplified.strip()

    def _normalize_translation_entry(
        self, raw_key: str, raw_value: object
    ) -> dict[str, str]:
        """Geminiレスポンス1件分を内部形式へ正規化"""
        if isinstance(raw_value, str):
            full_name = raw_value.strip() or raw_key
            return {"full": full_name, "short": full_name}

        if isinstance(raw_value, dict):
            full_name = str(
                raw_value.get("full") or raw_value.get("katakana") or ""
            ).strip()
            if not full_name:
                full_name = raw_key

            short_name = str(raw_value.get("short") or "").strip() or full_name
            return {"full": full_name, "short": short_name}

        return {"full": raw_key, "short": raw_key}

    def _align_translations_to_requested_names(
        self, requested_names: list[str], raw_translations: dict[str, object]
    ) -> dict[str, dict[str, str]]:
        """Geminiが返したキーを、要求時のAPI-Football名へ寄せて揃える"""
        normalized_requested: dict[str, list[str]] = {}
        for name in requested_names:
            normalized_requested.setdefault(self._normalize_name_key(name), []).append(
                name
            )

        aligned: dict[str, dict[str, str]] = {}
        for raw_key, raw_value in raw_translations.items():
            target_key = raw_key if raw_key in requested_names else None

            if target_key is None:
                candidates = normalized_requested.get(
                    self._normalize_name_key(raw_key), []
                )
                if len(candidates) == 1:
                    target_key = candidates[0]

            if target_key is None:
                continue

            aligned[target_key] = self._normalize_translation_entry(
                target_key, raw_value
            )

        for name in requested_names:
            aligned.setdefault(name, {"full": name, "short": name})

        return aligned

    def _build_unique_name_aliases(
        self, names: list[str], translations: dict[str, str]
    ) -> dict[str, str]:
        """一意に識別できる姓のみの別名を構築する"""
        alias_to_source: dict[str, list[str]] = {}
        for name in names:
            alias = self._extract_last_name_alias(name)
            if alias:
                alias_to_source.setdefault(alias, []).append(name)

        result: dict[str, str] = {}
        for alias, source_names in alias_to_source.items():
            if len(source_names) != 1:
                continue

            source_name = source_names[0]
            translated = translations.get(source_name, "")
            if translated and translated != source_name:
                result[alias] = translated

        return result

    def _extract_last_name_alias(self, name: str) -> str:
        """姓だけ表記されがちな末尾トークンを返す"""
        parts = name.split()
        if len(parts) < 2:
            return ""

        alias = parts[-1].strip()
        normalized = alias.replace("’", "'")
        if len(normalized.replace("'", "")) < 3:
            return ""

        return alias

    def _replace_alias_token(self, html: str, alias: str, translated: str) -> str:
        """英字の前後境界を見て、姓のみ表記を安全側で置換する"""
        result = html
        for source_variant in self._build_html_name_variants(alias):
            pattern = re.compile(
                rf"(?<![A-Za-z]){re.escape(source_variant)}(?![A-Za-z])"
            )
            result = pattern.sub(translated, result)
        return result

    def _build_html_name_variants(self, name: str) -> list[str]:
        """HTML中に現れうる同一名前の表記揺れを列挙する"""
        variants = [
            name,
            html.escape(name, quote=True),
            name.replace("'", "&#39;"),
            name.replace("'", "&#x27;"),
            name.replace("'", "&apos;"),
        ]

        deduped: list[str] = []
        for variant in variants:
            if variant not in deduped:
                deduped.append(variant)
        return deduped
