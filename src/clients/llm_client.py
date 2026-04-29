"""
LLM (Gemini / Claude) クライアント

LLM呼び出しを一元化し、モック対応・キャッシュ・ログ整形をここで行う。
モデル選択は `settings/gemini_prompts.py` の PROMPT_METADATA で
プロンプト単位に宣言され、`src/clients/llm_backends/` のバックエンド層が
具体的なAPIクライアント（Gemini / Anthropic）に振り分ける。
"""

import json
import logging
import os
from datetime import datetime

from config import config
from settings.cache_config import GROUNDING_TTL_DAYS
from settings.gemini_prompts import build_prompt, get_prompt_config
from src.clients.cache_store import CacheStore, create_cache_store
from src.clients.llm_backends import LLMResult, get_backend
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM クライアント（バックエンドはプロンプトごとに自動解決）"""

    def __init__(
        self, api_key: str = None, use_mock: bool = None, cache_store: CacheStore = None
    ):
        """
        Args:
            api_key: Gemini API Key（省略時はconfig.GOOGLE_API_KEY）
            use_mock: モックモード（省略時はconfig.USE_MOCK_DATA）
            cache_store: キャッシュストア（省略時は自動生成）
        """
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.use_mock = use_mock if use_mock is not None else config.USE_MOCK_DATA
        self.cache_store = cache_store or create_cache_store()
        self.use_grounding_cache = (
            os.getenv("USE_GROUNDING_CACHE", "True").lower() == "true"
        )

    def _call_backend(
        self,
        prompt_type: str,
        prompt: str,
    ) -> LLMResult:
        """PROMPT_METADATA に基づいてバックエンドを解決して呼び出す。"""
        prompt_config = get_prompt_config(prompt_type)
        backend_id = prompt_config.get("backend") or "gemini-flash"
        use_grounding = prompt_config.get("use_grounding", False)
        thinking_budget = prompt_config.get("thinking_budget")

        backend = get_backend(backend_id)
        result = backend.generate_text(
            prompt,
            use_grounding=use_grounding,
            thinking_budget=thinking_budget,
        )
        ApiStats.record_call(backend.name + ("/Grounding" if use_grounding else ""))
        return result

    def generate_content(self, prompt: str, prompt_type: str | None = None) -> str:
        """
        汎用的なLLM呼び出し。

        Args:
            prompt: プロンプト文字列
            prompt_type: PROMPT_METADATA のキー。指定するとそのバックエンドを使う。
                         省略時は gemini-flash（非Grounding）にフォールバック。

        Returns:
            生成されたテキスト
        """
        if self.use_mock:
            return "[MOCK] LLM response"

        try:
            if prompt_type:
                result = self._call_backend(prompt_type, prompt)
                return result.text

            # prompt_type 未指定の互換パス: gemini-flash 非Grounding
            backend = get_backend("gemini-flash")
            result = backend.generate_text(prompt, use_grounding=False)
            ApiStats.record_call(backend.name)
            return result.text
        except Exception as e:
            logger.error(f"LLM generate_content error: {e}")
            raise

    def generate_news_summary(self, home_team: str, away_team: str) -> str:
        """
        ニュース記事から試合前サマリーを生成（Grounding機能使用）
        """
        if self.use_mock:
            return self._get_mock_news_summary(home_team, away_team)

        prompt = build_prompt("news_summary", home_team=home_team, away_team=away_team)

        try:
            self._log_llm_request(
                "news_summary", prompt, home_team=home_team, away_team=away_team
            )
            result = self._call_backend("news_summary", prompt)
            self._log_llm_response("news_summary", result.text)
            return result.text
        except Exception as e:
            logger.error(f"Error generating news summary: {e}")
            return "エラーにつき取得不可（情報の取得に失敗しました）"

    def generate_tactical_preview(
        self,
        home_team: str,
        away_team: str,
        home_formation: str = "",
        away_formation: str = "",
        away_lineup: list[str] = None,
        home_lineup: list[str] = None,
        competition: str = "",
    ) -> str:
        """
        戦術プレビューを生成（Grounding機能使用）
        """
        if self.use_mock:
            return self._get_mock_tactical_preview(home_team, away_team)

        # Format lineups as comma-separated strings
        home_lineup_str = ", ".join(home_lineup) if home_lineup else "不明"
        away_lineup_str = ", ".join(away_lineup) if away_lineup else "不明"

        prompt = build_prompt(
            "tactical_preview",
            home_team=home_team,
            away_team=away_team,
            home_formation=home_formation or "不明",
            away_formation=away_formation or "不明",
            home_lineup=home_lineup_str,
            away_lineup=away_lineup_str,
            competition=competition or "欧州",
        )

        # Groundingキャッシュチェック
        cache_key = self._build_grounding_cache_key(
            "tactical_preview", home_team, away_team
        )
        cached_result = self._read_grounding_cache(cache_key, "tactical_preview")
        if cached_result:
            return cached_result

        try:
            self._log_llm_request(
                "tactical_preview",
                prompt,
                home_team=home_team,
                away_team=away_team,
                competition=competition,
            )
            result = self._call_backend("tactical_preview", prompt)

            # キャッシュ保存
            self._write_grounding_cache(cache_key, result.text)
            self._log_llm_response("tactical_preview", result.text)
            return result.text
        except Exception as e:
            logger.error(f"Error generating tactical preview: {e}")
            return "エラーにつき取得不可（情報の取得に失敗しました）"

    def check_spoiler(
        self, text: str, home_team: str, away_team: str
    ) -> tuple[bool, str]:
        """
        テキストがネタバレを含むかチェック（Issue #33）

        Returns:
            (is_safe, reason): 安全ならTrue、理由文字列
        """
        if self.use_mock:
            return True, "モックモード"

        # テキストの長さ制限を取得
        prompt_config = get_prompt_config("check_spoiler")
        text_limit = prompt_config.get("text_limit", 1500)

        prompt = build_prompt(
            "check_spoiler",
            home_team=home_team,
            away_team=away_team,
            text=text[:text_limit],
        )

        try:
            self._log_llm_request(
                "check_spoiler", prompt, home_team=home_team, away_team=away_team
            )
            response_text = self.generate_content(
                prompt, prompt_type="check_spoiler"
            ).strip()
            self._log_llm_response("check_spoiler", response_text)
            # マークダウンコードブロックを除去
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            result = json.loads(response_text)
            return result.get("is_safe", True), result.get("reason", "")
        except json.JSONDecodeError as e:
            logger.warning(f"Spoiler check JSON parse error: {e}")
            return True, "判定スキップ（JSON解析エラー）"
        except Exception as e:
            logger.warning(f"Spoiler check failed: {e}")
            return True, "判定スキップ（APIエラー）"

    def summarize_interview(
        self,
        team_name: str,
        opponent_team: str,
        is_home: bool,
        manager_name: str = None,
        opponent_manager_name: str = None,
    ) -> str:
        """
        インタビュー記事を要約（Gemini Grounding + REST API使用）
        """
        if self.use_mock:
            from src.mock_provider import MockProvider

            return MockProvider.get_interview_summary(team_name, opponent_team, is_home)

        # 監督名が指定されていない場合はデフォルト値
        manager_display = manager_name or "監督"
        opponent_manager_display = opponent_manager_name or "相手監督"
        match_info = f"{team_name} vs {opponent_team}"

        prompt = build_prompt(
            "interview",
            team_name=team_name,
            opponent_team=opponent_team,
            manager_name=manager_display,
            opponent_manager_name=opponent_manager_display,
            match_info=match_info,
        )

        # Groundingキャッシュチェック
        cache_key = self._build_grounding_cache_key(
            "interview", team_name, opponent_team
        )
        cached_result = self._read_grounding_cache(cache_key, "interview")
        if cached_result:
            return cached_result

        try:
            self._log_llm_request(
                "interview",
                prompt,
                team_name=team_name,
                opponent_team=opponent_team,
            )
            result = self._call_backend("interview", prompt)

            # キャッシュ保存
            self._write_grounding_cache(cache_key, result.text)
            self._log_llm_response("interview", result.text)
            return result.text

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Error summarizing interview for {team_name}: {error_type} - {e}"
            )
            return "エラーにつき取得不可（情報の取得に失敗しました）"

    def generate_transfer_news(
        self,
        team_name: str,
        match_date: str,
        transfer_window_context: str = "latest",
        is_home: bool = True,
    ) -> str:
        """
        移籍情報を生成（Grounding機能使用）
        """
        if self.use_mock:
            from src.mock_provider import MockProvider

            return MockProvider.get_transfer_news(team_name, match_date, is_home)

        prompt = build_prompt(
            "transfer_news",
            team_name=team_name,
            match_date=match_date,
            transfer_window_context=transfer_window_context,
        )

        # Groundingキャッシュチェック
        cache_key = self._build_grounding_cache_key(
            "transfer_news", team_name, match_date
        )
        cached_result = self._read_grounding_cache(cache_key, "transfer_news")
        if cached_result:
            return cached_result

        try:
            self._log_llm_request(
                "transfer_news",
                prompt,
                team_name=team_name,
                match_date=match_date,
            )
            result = self._call_backend("transfer_news", prompt)

            # キャッシュ保存
            self._write_grounding_cache(cache_key, result.text)
            self._log_llm_response("transfer_news", result.text)
            return result.text

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Error generating transfer news for {team_name}: {error_type} - {e}"
            )
            return "エラーにつき取得不可（情報の取得に失敗しました）"

    # ========== Grounding キャッシュヘルパー ==========

    def _build_grounding_cache_key(
        self, type_name: str, home_team: str, away_team: str
    ) -> str:
        """Grounding キャッシュキー（パス）を生成"""
        # ファイル名として安全なようにスペースを除去
        h = home_team.replace(" ", "")
        a = away_team.replace(" ", "")
        return f"grounding/{type_name}/{h}_vs_{a}.json"

    def _read_grounding_cache(self, cache_key: str, type_name: str) -> str | None:
        """Grounding キャッシュを読み込む"""
        if not self.use_grounding_cache:
            return None

        try:
            data = self.cache_store.read(cache_key)
            if data:
                # TTLチェック
                timestamp_str = data.get("timestamp")
                ttl_days = GROUNDING_TTL_DAYS.get(type_name, 7)

                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age_days = (datetime.now() - timestamp).days
                    if age_days < ttl_days:
                        logger.debug(f"[GROUNDING CACHE] HIT: {cache_key}")
                        # キャッシュヒットを記録
                        ApiStats.record_cache_hit("Gemini Grounding")
                        content = data.get("content")
                        self._log_llm_response(type_name, content, source="cache")
                        return content
                    else:
                        logger.info(f"[GROUNDING CACHE] EXPIRED: {cache_key}")
                else:
                    # タイムスタンプがない場合は古い形式か無期限扱い
                    logger.debug(f"[GROUNDING CACHE] HIT (no timestamp): {cache_key}")
                    ApiStats.record_cache_hit("Gemini Grounding")
                    content = data.get("content")
                    self._log_llm_response(type_name, content, source="cache")
                    return content
        except Exception as e:
            logger.warning(f"Failed to read grounding cache {cache_key}: {e}")

        return None

    def _write_grounding_cache(self, cache_key: str, content: str) -> None:
        """Grounding キャッシュを書き込む"""
        if not self.use_grounding_cache or not content:
            return

        try:
            from datetime import datetime

            data = {"timestamp": datetime.now().isoformat(), "content": content}
            self.cache_store.write(cache_key, data)
            logger.debug(f"[GROUNDING CACHE] SAVED: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to write grounding cache {cache_key}: {e}")

    def _log_llm_request(
        self, prompt_type: str, prompt: str, max_chars: int = 500, **params
    ):
        """LLMリクエストをログ出力"""
        params_str = (
            ", ".join(f"{k}={v}" for k, v in params.items()) if params else "no params"
        )
        logger.info(f"=== LLM Request [{prompt_type}] ({params_str}) ===")
        display = prompt[:max_chars] + "..." if len(prompt) > max_chars else prompt
        logger.info(f"Prompt ({len(prompt)} chars): {display}")
        logger.info(f"=== End LLM Request [{prompt_type}] ===")

    def _log_llm_response(
        self,
        prompt_type: str,
        response: str,
        max_chars: int = 3000,
        source: str = "api",
    ):
        """LLM応答をログ出力（長すぎる場合はtruncate）"""
        if not response:
            return
        display = (
            response[:max_chars] + "..." if len(response) > max_chars else response
        )
        logger.info(
            f"=== LLM Response [{prompt_type}] (source={source}, {len(response)} chars) ==="
        )
        logger.info(display)
        logger.info(f"=== End LLM Response [{prompt_type}] ===")

    # ========== モック用メソッド ==========

    def _get_mock_news_summary(self, home_team: str, away_team: str) -> str:
        from src.mock_provider import MockProvider

        return MockProvider.get_news_summary(home_team, away_team)

    def _get_mock_tactical_preview(self, home_team: str, away_team: str) -> str:
        from src.mock_provider import MockProvider

        return MockProvider.get_tactical_preview(home_team, away_team)

    def _get_mock_same_country_trivia(self, matchups: list[dict]) -> str:
        """モック用: 同国対決トリビア"""
        if not matchups:
            return ""
        lines = []
        for m in matchups:
            country = m.get("country", "Unknown")
            # パルサーが期待するフォーマットに合わせてモックを生成
            home_players = m.get("home_players", [])
            away_players = m.get("away_players", [])

            p1 = home_players[0] if home_players else "選手A"
            p2 = away_players[0] if away_players else "選手B"

            lines.append(f"🏳️ **{country}**")
            lines.append(
                f"**{p1}**（ホームチーム）と**{p2}**（アウェイチーム）。[モック: 関係性・小ネタ]"
            )
        return "\n\n".join(lines)

    # ========== 同国対決（Issue #39） ==========
    def generate_same_country_trivia(
        self, home_team: str, away_team: str, matchups: list[dict]
    ) -> str:
        """
        同国対決の関係性・小ネタを生成
        """
        if self.use_mock:
            return self._get_mock_same_country_trivia(matchups)

        if not matchups:
            return ""

        # マッチアップデータを整形
        matchup_texts = []
        for m in matchups:
            text = f"- 国籍: {m['country']}\n"
            text += (
                f"  ホームチーム選手 ({home_team}): {', '.join(m['home_players'])}\n"
            )
            text += (
                f"  アウェイチーム選手 ({away_team}): {', '.join(m['away_players'])}"
            )
            matchup_texts.append(text)

        matchup_context = "\n".join(matchup_texts)

        prompt = build_prompt("same_country_trivia", matchup_context=matchup_context)

        try:
            self._log_llm_request(
                "same_country_trivia",
                prompt,
                home_team=home_team,
                away_team=away_team,
            )
            result = self.generate_content(prompt, prompt_type="same_country_trivia")
            self._log_llm_response("same_country_trivia", result)
            return result
        except Exception as e:
            logger.error(f"Error generating same country trivia: {e}")
            return ""

    # ========== 古巣対決（Issue #20） ==========
    def generate_former_club_trivia(
        self,
        home_team: str,
        away_team: str,
        home_players: list[str],
        away_players: list[str],
        match_date: str = "",
    ) -> str:
        """
        古巣対決トリビアを生成（Gemini Grounding使用）
        """
        if self.use_mock:
            return self._get_mock_former_club_trivia(home_team, away_team)

        logger.info(
            "[FORMER_CLUB] Input players diagnostic: home_count=%d away_count=%d home_sample=%s away_sample=%s",
            len(home_players),
            len(away_players),
            home_players[:8],
            away_players[:8],
        )

        prompt = build_prompt(
            "former_club_trivia",
            home_team=home_team,
            away_team=away_team,
            home_players=", ".join(home_players),
            away_players=", ".join(away_players),
            match_date=match_date,
        )

        try:
            self._log_llm_request(
                "former_club_trivia",
                prompt,
                home_team=home_team,
                away_team=away_team,
                home_player_count=len(home_players),
                away_player_count=len(away_players),
            )
            result = self._call_backend("former_club_trivia", prompt)
            self._log_llm_response("former_club_trivia", result.text)
            return result.text
        except Exception as e:
            logger.error(f"Error generating former club trivia: {e}")
            return ""

    def _get_mock_former_club_trivia(self, home_team: str, away_team: str) -> str:
        """モック用: 古巣対決トリビア"""
        return f"- **選手A**（{away_team}）は{home_team}のアカデミー出身。[モック: 古巣対決トリビア]"

    def fact_check_former_club_batch(
        self,
        entries: list[dict],
        home_team: str,
        away_team: str,
    ) -> list[dict]:
        """
        古巣対決のファクトチェック（バッチ処理）
        """
        if self.use_mock:
            return [
                {
                    "player_name": e["player_name"],
                    "is_valid": True,
                    "reason": "モックモードにつき検証スキップ",
                }
                for e in entries
            ]

        if not entries:
            return []

        # エントリをJSON形式に整形
        entries_json = json.dumps(entries, ensure_ascii=False, indent=2)

        prompt = build_prompt(
            "former_club_fact_check",
            home_team=home_team,
            away_team=away_team,
            entries_json=entries_json,
        )

        try:
            self._log_llm_request(
                "former_club_fact_check",
                prompt,
                home_team=home_team,
                away_team=away_team,
                entry_count=len(entries),
            )
            response_text = self.generate_content(
                prompt, prompt_type="former_club_fact_check"
            ).strip()
            self._log_llm_response("former_club_fact_check", response_text)

            # マークダウンコードブロックを除去
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.split("```")[0]

            raw_results = json.loads(response_text)
            if not isinstance(raw_results, list):
                raise ValueError("Fact check response is not a JSON array")

            if len(raw_results) != len(entries):
                logger.warning(
                    f"Fact check result count mismatch: expected={len(entries)}, got={len(raw_results)}"
                )

            # 出力契約を強制: player_name/is_valid/reason を必ず揃える
            results = []
            for idx, entry in enumerate(entries):
                raw = raw_results[idx] if idx < len(raw_results) else {}
                if not isinstance(raw, dict):
                    raw = {}

                expected_name = str(entry.get("player_name", "Unknown"))
                player_name = str(raw.get("player_name") or expected_name)

                is_valid_raw = raw.get("is_valid")
                is_valid = is_valid_raw if isinstance(is_valid_raw, bool) else False

                reason_raw = raw.get("reason")
                reason = str(reason_raw).strip() if reason_raw is not None else ""
                if not reason:
                    reason = "reason未返却のため不採用"
                    is_valid = False

                if player_name != expected_name:
                    reason = (
                        f"{reason} / player_name補正: {player_name} -> {expected_name}"
                    )
                    player_name = expected_name

                results.append(
                    {
                        "player_name": player_name,
                        "is_valid": is_valid,
                        "reason": reason,
                    }
                )

            # ログ出力
            for result in results:
                player_name = result["player_name"]
                is_valid = result["is_valid"]
                reason = result["reason"]
                if is_valid:
                    logger.info(f"[FACT_CHECK] Approved {player_name}")
                else:
                    logger.warning(f"[FACT_CHECK] Rejected {player_name}: {reason}")

            return results

        except json.JSONDecodeError as e:
            logger.warning(
                f"Fact check JSON parse error: {e}. Output: {response_text[:200]}..."
            )
            # パース失敗時は全員パス
            return [
                {
                    "player_name": e["player_name"],
                    "is_valid": True,
                    "reason": "判定エラーにつきパス",
                }
                for e in entries
            ]
        except Exception as e:
            logger.warning(f"Fact check failed: {e}")
            return [
                {
                    "player_name": ent["player_name"],
                    "is_valid": True,
                    "reason": "判定エラーにつきパス",
                }
                for ent in entries
            ]
