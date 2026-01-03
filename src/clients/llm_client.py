"""
LLM (Gemini) クライアント

Gemini APIとのやり取りを一元化し、モック対応もここで行う。
ServiceはこのClientを通じてLLM機能を使用する。
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from config import config
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
            return "監督: 『重要な試合になる。選手たちは準備できている。』"
        
        if not articles:
            return "関連記事が見つかりませんでした"
        
        context = "\n".join([a['content'] for a in articles])
        
        prompt = f"""
Task: {team_name}の監督が試合前に語った内容を、**可能な限り原文のまま**日本語で要約してください。

## 優先順位
1. 監督の直接発言（カギカッコ引用を最優先）
2. 選手の直接発言
3. 記事から推測されるチーム状況

## 引用ルール
- 発言は必ずカギカッコ「」で囲む
- 誰の発言かを明記（例: グアルディオラ監督は「〜」と語った）
- 英語の発言は意訳してよいが、ニュアンスを保つ

## 除外対象
- 試合結果（スコア、勝敗）
- 監督の契約・後任問題
- 女子チームの情報

## 出力形式
- 前置き文（「はい、承知いたしました」等のAI応答文）は不要、本文のみ
- 【{team_name}】のようなチーム名プレフィックスは不要（UIで表示済み）
- 1800-2000字

Context:
{context}
"""
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Error summarizing interview for {team_name}: {error_type} - {e}")
            return f"要約エラー（{error_type}）"
    
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
            text = f"- 国籍: {m['country']}\\n"
            text += f"  ホームチーム選手 ({home_team}): {', '.join(m['home_players'])}\\n"
            text += f"  アウェイチーム選手 ({away_team}): {', '.join(m['away_players'])}"
            matchup_texts.append(text)
        
        matchup_context = "\\n".join(matchup_texts)
        
        prompt = f"""あなたはサッカー専門のトリビアライターです。

以下の同国対決について、選手間の関係性や興味深い事実（小ネタ）を日本語で記述してください。

対決カード:
{matchup_context}

Requirements:
1. 選手同士の関係性を優先的に記載:
   - 代表チームでの共演
   - 過去のクラブでの同僚関係
   - ユース時代の共演
2. 興味深いトリビアがあれば追加:
   - 同郷、同年齢
   - 過去の対戦エピソード
   - ライバル関係
3. 字数: 50-150字/国
4. 試合結果には絶対に言及しない
5. 確実な事実のみ記載（推測や不確かな情報は避ける）
6. 前置き文は不要、本文のみ

Output Format:
🇯🇵 **日本**
**選手A**（チームA）と**選手B**（チームB）。[関係性・小ネタ]
"""
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            logger.error(f"Error generating same country trivia: {e}")
            return ""
    

    
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
        
        prompt = f"""あなたはサッカー専門のトリビアライターです。

以下の同国対決について、選手間の関係性や興味深い事実（小ネタ）を日本語で記述してください。

対決カード:
{matchup_context}

Requirements:
1. 選手同士の関係性を優先的に記載:
   - 代表チームでの共演
   - 過去のクラブでの同僚関係
   - ユース時代の共演
2. 興味深いトリビアがあれば追加:
   - 同郷、同年齢
   - 過去の対戦エピソード
   - ライバル関係
3. 字数: 50-150字/国
4. 試合結果には絶対に言及しない
5. 確実な事実のみ記載（推測や不確かな情報は避ける）
6. 前置き文は不要、本文のみ

Output Format:
🇯🇵 **日本**
**選手A**（チームA）と**選手B**（チームB）。[関係性・小ネタ]
"""
        
        try:
            return self.generate_content(prompt)
        except Exception as e:
            logger.error(f"Error generating same country trivia: {e}")
            return ""

