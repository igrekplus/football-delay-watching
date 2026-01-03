"""
LLM (Gemini) クライアント

Gemini APIとのやり取りを一元化し、モック対応もここで行う。
ServiceはこのClientを通じてLLM機能を使用する。
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from config import config
from settings.gemini_prompts import build_prompt, get_prompt_config
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class LLMClient:
    """Gemini APIクライアント"""
    
    MODEL_NAME = "gemini-pro-latest"
    
    def __init__(self, api_key: str = None, use_mock: bool = None):
        """
        Args:
            api_key: Gemini API Key（省略時はconfig.GOOGLE_API_KEY）
            use_mock: モックモード（省略時はconfig.USE_MOCK_DATA）
        """
        self.api_key = api_key or config.GOOGLE_API_KEY
        self.use_mock = use_mock if use_mock is not None else config.USE_MOCK_DATA
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
    
    def generate_news_summary(
        self, 
        home_team: str, 
        away_team: str, 
        articles: List[Dict[str, str]]
    ) -> str:
        """
        ニュース記事から試合前サマリーを生成（Grounding機能使用）
        """
        if self.use_mock:
            return self._get_mock_news_summary(home_team, away_team)
        
        prompt = build_prompt('news_summary', home_team=home_team, away_team=away_team)
        
        try:
            from src.clients.gemini_rest_client import GeminiRestClient
            rest_client = GeminiRestClient(api_key=self.api_key)
            return rest_client.generate_content_with_grounding(prompt)
        except Exception as e:
            logger.error(f"Error generating news summary: {e}")
            return "エラーにつき取得不可（情報の取得に失敗しました）"
    
    def generate_tactical_preview(
        self, 
        home_team: str, 
        away_team: str, 
        articles: List[Dict[str, str]]
    ) -> str:
        """
        戦術プレビューを生成（Grounding機能使用）
        """
        if self.use_mock:
            return self._get_mock_tactical_preview(home_team, away_team)
        
        prompt = build_prompt('tactical_preview', home_team=home_team, away_team=away_team)
        
        try:
            from src.clients.gemini_rest_client import GeminiRestClient
            rest_client = GeminiRestClient(api_key=self.api_key)
            return rest_client.generate_content_with_grounding(prompt)
        except Exception as e:
            logger.error(f"Error generating tactical preview: {e}")
            return "エラーにつき取得不可（情報の取得に失敗しました）"
    
    def check_spoiler(
        self, 
        text: str, 
        home_team: str, 
        away_team: str
    ) -> Tuple[bool, str]:
        """
        テキストがネタバレを含むかチェック（Issue #33）
        
        Returns:
            (is_safe, reason): 安全ならTrue、理由文字列
        """
        if self.use_mock:
            return True, "モックモード"
        
        # テキストの長さ制限を取得
        config = get_prompt_config('check_spoiler')
        text_limit = config.get('text_limit', 1500)
        
        prompt = build_prompt(
            'check_spoiler', 
            home_team=home_team, 
            away_team=away_team, 
            text=text[:text_limit]
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
        articles: List[Dict[str, str]],
        opponent_team: str = None
    ) -> str:
        """
        インタビュー記事を要約（Gemini Grounding + REST API使用）
        
        Args:
            team_name: 対象チーム名
            articles: 記事リスト（現在は未使用、Groundingが検索）
            opponent_team: 対戦相手チーム名（この試合に限定するため）
        """
        if self.use_mock:
            return "監督: 『重要な試合になる。選手たちは準備できている。』"
        
        # 対戦相手が指定されている場合は明確に指定
        if opponent_team:
            match_info = f"{team_name} vs {opponent_team}"
            search_context = f"この試合（{match_info}）に限定してください。他の試合に関する情報は含めないでください。"
            search_query = opponent_team
            opponent_display = opponent_team
        else:
            match_info = f"{team_name}"
            search_context = "直近の試合に限定してください。"
            search_query = "latest"
            opponent_display = "直近の相手"

        prompt = build_prompt(
            'interview',
            team_name=team_name,
            match_info=match_info,
            search_query=search_query,
            search_context=search_context,
            opponent_display=opponent_display
        )
        
        try:
            from src.clients.gemini_rest_client import GeminiRestClient
            rest_client = GeminiRestClient(api_key=self.api_key)
            return rest_client.generate_content_with_grounding(prompt)
            
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Error summarizing interview for {team_name}: {error_type} - {e}")
            return "エラーにつき取得不可（情報の取得に失敗しました）"
    
    # ========== モック用メソッド ==========
    
    def _get_mock_news_summary(self, home_team: str, away_team: str) -> str:
        from src.mock_provider import MockProvider
        return MockProvider.get_news_summary(home_team, away_team)
    
    def _get_mock_tactical_preview(self, home_team: str, away_team: str) -> str:
        from src.mock_provider import MockProvider
        return MockProvider.get_tactical_preview(home_team, away_team)
    
    def _get_mock_same_country_trivia(self, matchups: List[Dict]) -> str:
        """モック用: 同国対決トリビア"""
        if not matchups:
            return ""
        lines = []
        for m in matchups:
            country = m.get("country", "Unknown")
            home = ", ".join(m.get("home_players", []))
            away = ", ".join(m.get("away_players", []))
            lines.append(f"🏳️ **{country}** **{home}** vs **{away}**。[モック: 関係性・小ネタ]")
        return "\\n\\n".join(lines)
    

    # ========== 同国対決（Issue #39） ==========    
    def generate_same_country_trivia(
        self,
        home_team: str,
        away_team: str,
        matchups: List[Dict]
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
            text += f"  ホームチーム選手 ({home_team}): {', '.join(m['home_players'])}\n"
            text += f"  アウェイチーム選手 ({away_team}): {', '.join(m['away_players'])}"
            matchup_texts.append(text)
        
        matchup_context = "\n".join(matchup_texts)
        
        prompt = build_prompt('same_country_trivia', matchup_context=matchup_context)
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            logger.error(f"Error generating same country trivia: {e}")
            return ""

