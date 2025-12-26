from typing import List, Dict, Any
from config import config
from src.domain.models import MatchData
from src.utils.spoiler_filter import SpoilerFilter
import logging

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.filter = SpoilerFilter()

    def process_news(self, matches: List[MatchData]):
        for match in matches:
            if match.is_target:
                logger.info(f"Processing news for {match.home_team} vs {match.away_team}")
                # 1. Collect
                articles = self._collect_news(match)
                
                # 2. Generate Summary
                # Pass full article objects (with source) to generator
                raw_summary = self._generate_summary(match, articles)
                match.news_summary = self.filter.check_text(raw_summary)
                
                # Issue #33: Geminiで結果言及をチェック
                if raw_summary and not config.USE_MOCK_DATA:
                    is_safe, reason = self._check_spoiler_with_llm(raw_summary, match)
                    if not is_safe:
                        logger.warning(f"  [SPOILER CHECK] {match.home_team} vs {match.away_team}: {reason}")
                        match.news_summary = f"⚠️ 結果言及の可能性あり: {reason}\n\n{match.news_summary}"
                
                # 3. Generate Tactical Preview
                raw_preview = self._generate_tactical_preview(match, articles)
                match.tactical_preview = self.filter.check_text(raw_preview)
                match.preview_url = "https://example.com/tactical-preview"
                
                # 4. Append Sources to Summary (for report display)
                if articles:
                   sources_text = "\n\n**Sources:**\n" + "\n".join([f"- {a['source']}: [{a['title']}]({a['url']})" for a in articles])
                   match.news_summary += sources_text
                
                # 5. Collect and Generate Interviews
                self._process_interviews(match)

    def _collect_news(self, match: MatchData) -> List[Dict[str, str]]:
        if config.USE_MOCK_DATA:
            return self._get_mock_news(match)
        else:
            return self._search_news_google(match)

    def _search_news_google(self, match: MatchData) -> List[Dict[str, str]]:
        import requests
        
        # Google Custom Search API
        url = "https://www.googleapis.com/customsearch/v1"
        # Issue #34: 女子チームを除外し、対戦関連記事を優先
        query = f'"{match.home_team}" "{match.away_team}" match preview -women -WFC -WSL -女子'
        
        params = {
            "key": config.GOOGLE_SEARCH_API_KEY,
            "cx": config.GOOGLE_SEARCH_ENGINE_ID,
            "q": query,
            "dateRestrict": "d2",
            "gl": "jp" if "Japan" in match.competition else "us",
            "num": config.NEWS_SEARCH_LIMIT
        }
        
        articles = []
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'items' not in data:
                logger.warning(f"No headlines found for {match.home_team} vs {match.away_team}")
                return []
                
            for item in data['items']:
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                link = item.get('link', '')
                display_link = item.get('displayLink', 'Unknown Source')
                
                content_text = f"{title}\n{snippet}"
                
                if self.filter.is_safe_article(content_text):
                    # Issue #34: 両チーム名を含むかスコアを計算
                    content_lower = content_text.lower()
                    relevance_score = 0
                    if match.home_team.lower() in content_lower:
                        relevance_score += 1
                    if match.away_team.lower() in content_lower:
                        relevance_score += 1
                        
                    articles.append({
                        "content": content_text,
                        "title": title,
                        "source": display_link,
                        "url": link,
                        "relevance_score": relevance_score
                    })
                    logger.info(f"  [ACCEPTED] {title} ({display_link}) relevance={relevance_score}")
                else:
                    logger.info(f"  [REJECTED] {title} (Spoiler detected)")
            
            # Issue #34: 両チーム名を含む記事を優先してソート
            articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                    
            if not articles:
                match.error_status = config.ERROR_MINOR
                logger.warning(f"No safe articles found after filtering for {match.id}")
                
            return articles

        except Exception as e:
            logger.error(f"Error searching news for {match.id}: {e}")
            match.error_status = config.ERROR_MINOR
            return []

    def _get_mock_news(self, match: MatchData) -> List[Dict[str, str]]:
        # Real-style mock news for Manchester City vs West Ham
        return [
            {"content": f"Premier League preview: {match.home_team} host {match.away_team} at Etihad Stadium. Guardiola's side looking to continue their dominance.", 
             "title": f"{match.home_team} vs {match.away_team}: Premier League Preview", "source": "www.bbc.com", "url": "https://www.bbc.com/sport"},
            {"content": f"Lucas Paqueta will be key for {match.away_team}. His creativity and passing could unlock City's defense.", 
             "title": "Paqueta's role vital for West Ham", "source": "www.skysports.com", "url": "https://www.skysports.com"},
            {"content": "Haaland has scored in his last 5 Premier League games. The Norwegian striker is in phenomenal form.", 
             "title": "Haaland's scoring streak continues", "source": "www.goal.com", "url": "https://www.goal.com"}
        ]

    def _generate_summary(self, match: MatchData, articles: List[Dict[str, str]]) -> str:
        if config.USE_MOCK_DATA:
            return self._get_mock_summary(match, articles)
        else:
            return self._call_llm(match, articles, "SUMMARY")

    def _generate_tactical_preview(self, match: MatchData, articles: List[Dict[str, str]]) -> str:
        if config.USE_MOCK_DATA:
            return self._get_mock_preview(match, articles)
        else:
            return self._call_llm(match, articles, "PREVIEW")

    def _call_llm(self, match: MatchData, articles: List[Dict[str, str]], mode: str) -> str:
        import google.generativeai as genai
        
        if not articles:
            return "No articles found to generate content."
            
        genai.configure(api_key=config.GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-pro-latest") 
        
        # Construct Prompt using 'content' field
        context_lines = [a['content'] for a in articles]
        context = "\n".join(context_lines)
        
        # Issue #29: 前置き文禁止・本文のみ出力を明記
        if mode == "SUMMARY":
            prompt = f"""
            Task: Summarize the following news snippets for '{match.home_team} vs {match.away_team}' into a Japanese pre-match summary (600-1000 chars).
            
            Constraints:
            - Do NOT reveal results. Check sources provided in context if needed.
            - 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。
            
            Context:
            {context}
            """
        else: # PREVIEW
            prompt = f"""
            Task: Extract tactical analysis for '{match.home_team} vs {match.away_team}' (Japanese).
            
            Constraints:
            - Focus on likely formations and matchups. Do NOT reveal results.
            - 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。
            - 最初の一文から戦術分析の内容を開始してください。
            
            Context:
            {context}
            """
            
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error calling LLM for {mode}: {e}")
            return f"Error generating {mode}"

    def _get_mock_summary(self, match: MatchData, articles: List[Dict[str, str]]) -> str:
        # Real-style mock summary for layout testing
        return f"""プレミアリーグの注目カード、{match.home_team}対{match.away_team}の一戦が間近に迫り、多くのサッカーメディアやファンが試合のプレビューを発信し、期待感を高めている。

昨シーズンの王者である{match.home_team}は、今季もその圧倒的な攻撃力と組織的な守備でリーグを席巻している。ホームで迎えるこの一戦でも、盤石の試合運びで確実に勝ち点を狙ってくるだろう。

対する{match.away_team}は、強敵シティにアウェイで挑む形となる。チームの創造性の中心を担うのは、ブラジル代表のルーカス・パケタだ。彼の卓越したテクニックとパスセンスが、シティの堅固な守備陣をこじ開ける鍵となることは間違いない。

試合の焦点は、シティが誇るボール支配に対し、{match.away_team}がいかにして効果的なカウンターを仕掛けられるかという点にある。王者シティがその強さを見せつけるのか、それとも{match.away_team}がキーマン・パケタを中心に一矢報いるのか。"""

    def _get_mock_preview(self, match: MatchData, articles: List[Dict[str, str]]) -> str:
        # Real-style tactical preview for layout testing
        return f"""### {match.home_team} vs {match.away_team}：戦術分析プレビュー

プレミアリーグ屈指の戦術的な対決となるこの一戦は、対照的なスタイルを持つ両チームの激突が予想される。

**{match.home_team}の予想フォーメーション: 4-2-3-1**
- グアルディオラ監督のチームは、圧倒的なボールポゼッションで試合を支配することを目指す
- 最前線のハーランドをターゲットに、両翼のウインガーがハーフスペースを利用

**{match.away_team}の予想フォーメーション: 4-5-1**
- 自陣でコンパクトな守備ブロックを形成し、シティの攻撃スペースを消す
- ボーウェンのスピードとパケタの創造性がカウンターの起点

**注目のマッチアップ:**
1. ハーランド vs ウェストハムのCB - フィジカルとポジショニングの攻防
2. ロドリ vs パケタ - 中盤の主導権争い
3. シティのウインガー vs サイドバック - 1対1の勝負"""

    def _check_spoiler_with_llm(self, text: str, match: MatchData) -> tuple:
        """Issue #33: Geminiで結果言及の可能性を判定
        
        Returns:
            tuple: (is_safe: bool, reason: str)
        """
        import google.generativeai as genai
        import json
        
        genai.configure(api_key=config.GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-pro-latest")
        
        prompt = f"""以下のテキストが「{match.home_team} vs {match.away_team}」の試合結果を言及しているかを判定してください。

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
            response = model.generate_content(prompt)
            # JSONを抽出
            response_text = response.text.strip()
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

    def _process_interviews(self, match: MatchData):
        """Search and summarize pre-match interviews for both teams"""
        if config.USE_MOCK_DATA:
            match.home_interview = f"【{match.home_team}】監督: 『重要な試合になる。選手たちは準備できている。』"
            match.away_interview = f"【{match.away_team}】監督: 『難しいアウェイ戦だが、勝ち点3を持ち帰りたい。』"
            return
        
        # Search interviews for each team
        for is_home in [True, False]:
            team_name = match.home_team if is_home else match.away_team
            interview_articles = self._search_interviews(team_name)
            
            if interview_articles:
                summary = self._summarize_interview(team_name, interview_articles)
                summary = self.filter.check_text(summary)
                
                if is_home:
                    match.home_interview = summary
                else:
                    match.away_interview = summary
            else:
                if is_home:
                    match.home_interview = "インタビュー記事が見つかりませんでした"
                else:
                    match.away_interview = "インタビュー記事が見つかりませんでした"
    
    def _search_interviews(self, team_name: str) -> List[Dict[str, str]]:
        """Search for manager and player interviews for a team"""
        import requests
        
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Improved queries to find actual quotes and statements
        # Exclude women's teams (-women -WFC -WSL)
        queries = [
            f'"{team_name}" manager "said" OR "says" OR "quotes" press conference Premier League -result -score -twitter.com -x.com -women -WFC -WSL',
            f'"{team_name}" player interview "said" OR "reveals" OR "admits" Premier League -result -score -twitter.com -x.com -women -WFC -WSL'
        ]
        
        all_articles = []
        
        for query in queries:
            params = {
                "key": config.GOOGLE_SEARCH_API_KEY,
                "cx": config.GOOGLE_SEARCH_ENGINE_ID,
                "q": query,
                "dateRestrict": "d7",  # Last 7 days for better coverage
                "gl": "uk",  # UK for Premier League news
                "num": 5  # Increase limit per query
            }
            
            try:
                response = requests.get(url, params=params)
                data = response.json()
                
                if 'items' not in data:
                    logger.info(f"  [INTERVIEW] {team_name}: 検索結果なし (query: {query[:50]}...)")
                    continue
                    
                for item in data['items']:
                    title = item.get('title', '')
                    snippet = item.get('snippet', '')
                    content_text = f"{title}\n{snippet}"
                    
                    if self.filter.is_safe_article(content_text):
                        all_articles.append({
                            "content": content_text,
                            "title": title,
                            "source": item.get('displayLink', 'Unknown')
                        })
                        logger.info(f"  [INTERVIEW] {title}")
                        
            except Exception as e:
                logger.error(f"Error searching interviews for {team_name}: {e}")
        
        if not all_articles:
            logger.info(f"  [INTERVIEW] {team_name}: 関連記事が見つかりませんでした")
        return all_articles[:4]  # Max 4 articles per team
    
    def _summarize_interview(self, team_name: str, articles: List[Dict[str, str]]) -> str:
        """Summarize interview articles using Gemini"""
        import google.generativeai as genai
        
        if not articles:
            # Issue #31: 記事なしの理由を明確化
            return f"【{team_name}】関連記事が見つかりませんでした"
            
        genai.configure(api_key=config.GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-pro-latest")
        
        context = "\n".join([a['content'] for a in articles])
        
        prompt = f"""
        Task: 以下のニュース記事から、{team_name}の監督や選手の試合前コメントを日本語で要約してください（200-300字）。
        Format: 【{team_name}】で始めて、監督や選手の発言を引用形式で含めてください。
        Constraint: 試合結果に関する情報は絶対に含めないでください。
        
        Context:
        {context}
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # Issue #31: APIエラー理由を明確化
            error_type = type(e).__name__
            logger.error(f"Error summarizing interview for {team_name}: {error_type} - {e}")
            return f"【{team_name}】要約エラー（{error_type}）"
