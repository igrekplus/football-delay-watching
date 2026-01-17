"""
LLM (Gemini) クライアント

Gemini APIとのやり取りを一元化し、モック対応もここで行う。
ServiceはこのClientを通じてLLM機能を使用する。
"""

import json
import logging
import os

from config import config
from settings.cache_config import GROUNDING_TTL_DAYS
from settings.gemini_prompts import build_prompt, get_prompt_config
from src.clients.cache_store import CacheStore, create_cache_store
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class LLMClient:
    """Gemini APIクライアント"""

    MODEL_NAME = "gemini-pro-latest"

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
        self._model = None

    def _get_model(self):
        """モデルを遅延初期化"""
        if self._model is None and not self.use_mock:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.MODEL_NAME)
        return self._model

    def generate_content(self, prompt: str) -> str:
        """
        汎用的なLLM呼び出し

        Args:
            prompt: プロンプト文字列

        Returns:
            生成されたテキスト
        """
        if self.use_mock:
            return "[MOCK] LLM response"

        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            # API呼び出しを記録
            ApiStats.record_call("Gemini API")
            return response.text
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
            from src.clients.gemini_rest_client import GeminiRestClient

            rest_client = GeminiRestClient(api_key=self.api_key)
            result = rest_client.generate_content_with_grounding(prompt)
            # API呼び出しを記録
            ApiStats.record_call("Gemini Grounding")
            return result
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

        Args:
            home_team: ホームチーム名
            away_team: アウェイチーム名
            articles: 記事リスト（現在は未使用、Groundingが検索）
            home_formation: ホームチームのフォーメーション（例: "4-2-3-1"）
            away_formation: アウェイチームのフォーメーション（例: "4-4-2"）
            home_lineup: ホームチームのスタメンリスト
            away_lineup: アウェイチームのスタメンリスト
            competition: 大会名（例: "Premier League", "La Liga"）
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
            from src.clients.gemini_rest_client import GeminiRestClient

            rest_client = GeminiRestClient(api_key=self.api_key)
            result = rest_client.generate_content_with_grounding(prompt)

            # API呼び出しを記録
            ApiStats.record_call("Gemini Grounding")

            # キャッシュ保存
            self._write_grounding_cache(cache_key, result)
            return result
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
        config = get_prompt_config("check_spoiler")
        text_limit = config.get("text_limit", 1500)

        prompt = build_prompt(
            "check_spoiler",
            home_team=home_team,
            away_team=away_team,
            text=text[:text_limit],
        )

        try:
            response_text = self.generate_content(prompt).strip()
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
        manager_name: str = None,
        opponent_manager_name: str = None,
    ) -> str:
        """
        インタビュー記事を要約（Gemini Grounding + REST API使用）

        Args:
            team_name: 対象チーム名
            opponent_team: 対戦相手チーム名
            manager_name: 監督名（省略時は「監督」を使用）
            opponent_manager_name: 対戦相手の監督名（省略時は「相手監督」を使用）
        """
        if self.use_mock:
            from src.mock_provider import MockProvider
            # Determine if home or away based on team_name (simplified logic for now, assumes caller context)
            # Actually summarize_interview arguments don't strictly say who is home/away easily without context
            # But usually team_name is the target.
            # Let's assume team_name is what we look for.
            # To be safe, we might need a way to know if it's home or away.
            # In news_service.py:
            # team_name = match.core.home_team if is_home else match.core.away_team
            # opponent_team = match.core.away_team if is_home else match.core.home_team
            # So we can imply is_home by checking if team_name is home in the match context found in MockProvider?
            # MockProvider.get_interview_summary takes (team, opponent, is_home).
            # We can pass is_home=True temporarily and let MockProvider handle it or just pass names.
            # Re-reading my MockProvider update:
            # get_interview_summary(cls, team_name: str, opponent_team: str, is_home: bool)
            # home = cls._normalize_team_name(team_name if is_home else opponent_team)
            # If is_home=True, home=team_name. If is_home=False, home=opponent_team.
            # This works. matching the logic in news_service.

            # Use a heuristic or check MockProvider data?
            # Simplest: Check matches in MockProvider?
            # Or just pass is_home=True if we treat the first arg as "primary/home in this context"
            # BUT wait, the file naming is home_away.json.
            # We need to correctly identify which team is home in the fixture.
            matches = MockProvider.get_matches()
            is_fixture_home = False
            for m in matches:
                if m.core.home_team == team_name:
                    is_fixture_home = True
                    break

            return MockProvider.get_interview_summary(
                team_name, opponent_team, is_fixture_home
            )

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
            from src.clients.gemini_rest_client import GeminiRestClient

            rest_client = GeminiRestClient(api_key=self.api_key)
            result = rest_client.generate_content_with_grounding(prompt)

            # API呼び出しを記録
            ApiStats.record_call("Gemini Grounding")

            # キャッシュ保存
            self._write_grounding_cache(cache_key, result)
            return result

        except Exception as e:
            error_type = type(e).__name__
            logger.error(
                f"Error summarizing interview for {team_name}: {error_type} - {e}"
            )
            return "エラーにつき取得不可（情報の取得に失敗しました）"

    def generate_transfer_news(
        self, team_name: str, match_date: str, transfer_window_context: str = "latest"
    ) -> str:
        """
        移籍情報を生成（Grounding機能使用）

        Args:
            team_name: チーム名
            match_date: 試合開催日 (YYYY-MM-DD)
            transfer_window_context: 検索用コンテキスト（デフォルト "latest"）
        """
        if self.use_mock:
            from src.mock_provider import MockProvider

            return MockProvider.get_transfer_news(
                team_name, match_date, is_home=True
            )  # is_home logic is inside get_transfer_news now

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
            from src.clients.gemini_rest_client import GeminiRestClient

            rest_client = GeminiRestClient(api_key=self.api_key)
            result = rest_client.generate_content_with_grounding(prompt)

            # API呼び出しを記録
            ApiStats.record_call("Gemini Grounding")

            # キャッシュ保存
            self._write_grounding_cache(cache_key, result)
            return result

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
                from datetime import datetime

                timestamp_str = data.get("timestamp")
                ttl_days = GROUNDING_TTL_DAYS.get(type_name, 7)

                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    age_days = (datetime.now() - timestamp).days
                    if age_days < ttl_days:
                        logger.info(f"[GROUNDING CACHE] HIT: {cache_key}")
                        # キャッシュヒットを記録
                        ApiStats.record_cache_hit("Gemini Grounding")
                        return data.get("content")
                    else:
                        logger.info(f"[GROUNDING CACHE] EXPIRED: {cache_key}")
                else:
                    # タイムスタンプがない場合は古い形式か無期限扱い
                    logger.info(f"[GROUNDING CACHE] HIT (no timestamp): {cache_key}")
                    ApiStats.record_cache_hit("Gemini Grounding")
                    return data.get("content")
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

        Args:
            home_team: ホームチーム名
            away_team: アウェイチーム名
            matchups: 検出されたマッチアップリスト
                [{"country": "Japan", "home_players": [...], "away_players": [...]}]

        Returns:
            関係性・小ネタを含むテキスト（日本語）
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
            return self.generate_content(prompt)
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
    ) -> str:
        """
        古巣対決トリビアを生成（Gemini Grounding使用）

        Args:
            home_team: ホームチーム名
            away_team: アウェイチーム名
            home_players: ホームチームの全選手リスト
            away_players: アウェイチームの全選手リスト

        Returns:
            古巣対決トリビアテキスト（日本語）
        """
        if self.use_mock:
            return self._get_mock_former_club_trivia(home_team, away_team)

        prompt = build_prompt(
            "former_club_trivia",
            home_team=home_team,
            away_team=away_team,
            home_players=", ".join(home_players),
            away_players=", ".join(away_players),
        )

        try:
            from src.clients.gemini_rest_client import GeminiRestClient

            rest_client = GeminiRestClient(api_key=self.api_key)
            result = rest_client.generate_content_with_grounding(prompt)
            # API呼び出しを記録
            ApiStats.record_call("Gemini Grounding")
            return result
        except Exception as e:
            logger.error(f"Error generating former club trivia: {e}")
            return ""

    def _get_mock_former_club_trivia(self, home_team: str, away_team: str) -> str:
        """モック用: 古巣対決トリビア"""
        return f"- **選手A**（{away_team}）は{home_team}のアカデミー出身。[モック: 古巣対決トリビア]"
