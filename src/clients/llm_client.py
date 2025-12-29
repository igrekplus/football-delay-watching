"""
LLM (Gemini) クライアント

Gemini APIとのやり取りを一元化し、モック対応もここで行う。
ServiceはこのClientを通じてLLM機能を使用する。
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from config import config

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
        ニュース記事から試合前サマリーを生成
        
        Args:
            home_team: ホームチーム名
            away_team: アウェイチーム名
            articles: 記事リスト（content, title, source, url）
        """
        if self.use_mock:
            return self._get_mock_news_summary(home_team, away_team)
        
        if not articles:
            return "No articles found to generate content."
        
        context = "\n".join([a['content'] for a in articles])
        
        prompt = f"""
        Task: Summarize the following news snippets for '{home_team} vs {away_team}' into a Japanese pre-match summary (600-1000 chars).
        
        Constraints:
        - Do NOT reveal results. Check sources provided in context if needed.
        - 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。
        
        Context:
        {context}
        """
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            logger.error(f"Error generating news summary: {e}")
            return "Error generating summary"
    
    def generate_tactical_preview(
        self, 
        home_team: str, 
        away_team: str, 
        articles: List[Dict[str, str]]
    ) -> str:
        """
        戦術プレビューを生成
        """
        if self.use_mock:
            return self._get_mock_tactical_preview(home_team, away_team)
        
        if not articles:
            return "No articles found to generate content."
        
        context = "\n".join([a['content'] for a in articles])
        
        prompt = f"""
        Task: Extract tactical analysis for '{home_team} vs {away_team}' (Japanese).
        
        Constraints:
        - Focus on likely formations and matchups. Do NOT reveal results.
        - 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。
        - 最初の一文から戦術分析の内容を開始してください。
        
        Context:
        {context}
        """
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            logger.error(f"Error generating tactical preview: {e}")
            return "Error generating preview"
    
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
        
        prompt = f"""以下のテキストが「{home_team} vs {away_team}」の試合結果を言及しているかを判定してください。

テキスト:
{text[:1500]}

判定基準:
- スコア（例: 2-1, 3-0）の記載
- 勝敗の記載（例: 〇〇が勝利、敗北、won, lost）
- ゴールを決めた選手名（得点者）

回答は以下のJSON形式のみで（説明不要）:
{{"is_safe": true, "reason": "なし"}} または {{"is_safe": false, "reason": "理由"}}
"""
        
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
        articles: List[Dict[str, str]]
    ) -> str:
        """
        インタビュー記事を要約
        """
        if self.use_mock:
            return f"【{team_name}】監督: 『重要な試合になる。選手たちは準備できている。』"
        
        if not articles:
            return f"【{team_name}】関連記事が見つかりませんでした"
        
        context = "\n".join([a['content'] for a in articles])
        
        prompt = f"""
        Task: 以下のニュース記事から、{team_name}の監督や選手の試合前コメントを日本語で要約してください（200-300字）。
        Format: 【{team_name}】で始めて、監督や選手の発言を引用形式で含めてください。
        Constraint: 試合結果に関する情報は絶対に含めないでください。
        
        Context:
        {context}
        """
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Error summarizing interview for {team_name}: {error_type} - {e}")
            return f"【{team_name}】要約エラー（{error_type}）"
    
    # ========== モック用メソッド ==========
    
    def _get_mock_news_summary(self, home_team: str, away_team: str) -> str:
        from src.mock_provider import MockProvider
        return MockProvider.get_news_summary(home_team, away_team)
    
    def _get_mock_tactical_preview(self, home_team: str, away_team: str) -> str:
        from src.mock_provider import MockProvider
        return MockProvider.get_tactical_preview(home_team, away_team)

