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
        インタビュー記事を要約（Gemini Grounding + REST API使用）
        """
        if self.use_mock:
            return "監督: 『重要な試合になる。選手たちは準備できている。』"
        
        # Groundingを使用するため、articlesの内容は直接コンテキストとして渡さず、
        # プロンプト内で検索指示として活用する、または単に検索キーワードの参考にする
        # 現状のPoCプロンプトに従い、検索クエリ自体をプロンプトに埋め込む形式を採用
        
        # 相手チーム名をarticlesから推測するのは難しいため、
        # 呼び出し元で相手チーム名が渡されていない現状のシグネチャでは完全ではないが、
        # 検索クエリで "vs opponent" の部分はLLMに推測させるか、
        # または呼び出し元を変更する必要がある。
        # いったん、現状の引数 (team_name) だけで最大限努力するプロンプトにする。
        # ※理想的には相手チーム名も引数に欲しいが、呼び出し元の変更を避けるため
        # プロンプトで「直近の対戦相手」を探させる。

        prompt = f"""
Task: {team_name}の監督が、直近の試合（または次の試合）に関して語った最新のコメントや記者会見の内容を検索し、日本語で要約してください。

## 検索指示
- "{team_name} manager press conference quotes latest"
- "{team_name} vs next opponent manager quotes"
- などのクエリで最新情報を探してください。
- 直近（24-48時間以内）の情報を優先してください。

## 要約の要件
- 監督の具体的な発言があれば、可能な限りカギカッコ「」で原文のニュアンスを残して引用してください。
- 試合結果（スコアなど）が既に判明している場合は、**絶対に結果には触れず**、試合前のコメントとして構成してください。
- 確実な情報源（BBC, Sky Sports, 公式サイト等）に基づいていることを重視してください。
- **文字数: 1800-2000字程度（非常に詳細に記述してください）**
- 以下の点について詳しく記述してください：
    - 怪我人・復帰選手の詳細な状況
    - 対戦相手に対する具体的な評価・分析
    - 今後の過密日程やシーズン全体の展望に対する言及
    - 記者との質疑応答における興味深いやり取り

## 出力形式
- 本文のみ
"""
        
        try:
            # 遅延インポート（循環参照回避のため）
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

