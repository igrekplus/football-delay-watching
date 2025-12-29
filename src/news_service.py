"""
ニュースサービス

試合関連のニュース収集・要約・フィルタリングを担当する。
API呼び出しはClientに委譲し、ビジネスロジックに専念する。
"""

from typing import List, Dict
import logging

from config import config
from src.domain.models import MatchData
from src.utils.spoiler_filter import SpoilerFilter
from src.clients.llm_client import LLMClient
from src.clients.google_search_client import GoogleSearchClient

logger = logging.getLogger(__name__)


class NewsService:
    """ニュース収集・要約サービス"""
    
    def __init__(
        self, 
        llm_client: LLMClient = None, 
        search_client: GoogleSearchClient = None
    ):
        """
        Args:
            llm_client: LLMクライアント（DIで注入可能）
            search_client: 検索クライアント（DIで注入可能）
        """
        self.filter = SpoilerFilter()
        self.llm = llm_client or LLMClient()
        self.search = search_client or GoogleSearchClient()

    def process_news(self, matches: List[MatchData]):
        """試合リストに対してニュース処理を実行"""
        for match in matches:
            if match.is_target:
                logger.info(f"Processing news for {match.home_team} vs {match.away_team}")
                
                # 1. Collect articles
                articles = self._collect_news(match)
                
                # 2. Generate Summary
                raw_summary = self._generate_summary(match, articles)
                match.news_summary = self.filter.check_text(raw_summary)
                
                # 3. Spoiler check with LLM (Issue #33)
                if raw_summary and not config.USE_MOCK_DATA:
                    is_safe, reason = self.llm.check_spoiler(
                        raw_summary, 
                        match.home_team, 
                        match.away_team
                    )
                    if not is_safe:
                        logger.warning(f"  [SPOILER CHECK] {match.home_team} vs {match.away_team}: {reason}")
                        match.news_summary = f"⚠️ 結果言及の可能性あり: {reason}\n\n{match.news_summary}"
                
                # 4. Generate Tactical Preview
                raw_preview = self._generate_tactical_preview(match, articles)
                match.tactical_preview = self.filter.check_text(raw_preview)
                match.preview_url = "https://example.com/tactical-preview"
                
                # 5. Append Sources (Issue #54)
                if articles:
                    sources_list = "\n".join([
                        f'<li><a href="{a["url"]}" target="_blank">{a["title"]}</a> ({a["source"]})</li>' 
                        for a in articles
                    ])
                    sources_text = f'\n\n<details>\n<summary><strong>📚 Sources ({len(articles)}件)</strong></summary>\n<ul>\n{sources_list}\n</ul>\n</details>'
                    match.news_summary += sources_text
                
                # 6. Process Interviews
                self._process_interviews(match)

    def _collect_news(self, match: MatchData) -> List[Dict[str, str]]:
        """ニュース記事を収集"""
        articles = self.search.search_news(
            home_team=match.home_team,
            away_team=match.away_team,
            competition=match.competition
        )
        
        # フィルタリング: スポイラーを含む記事を除外
        safe_articles = []
        for article in articles:
            if self.filter.is_safe_article(article['content']):
                safe_articles.append(article)
                logger.info(f"  [ACCEPTED] {article['title']} ({article['source']})")
            else:
                logger.info(f"  [REJECTED] {article['title']} (Spoiler detected)")
        
        if not safe_articles:
            match.error_status = config.ERROR_MINOR
            logger.warning(f"No safe articles found after filtering for {match.id}")
        
        return safe_articles

    def _generate_summary(self, match: MatchData, articles: List[Dict[str, str]]) -> str:
        """ニュース要約を生成"""
        return self.llm.generate_news_summary(
            home_team=match.home_team,
            away_team=match.away_team,
            articles=articles
        )

    def _generate_tactical_preview(self, match: MatchData, articles: List[Dict[str, str]]) -> str:
        """戦術プレビューを生成"""
        return self.llm.generate_tactical_preview(
            home_team=match.home_team,
            away_team=match.away_team,
            articles=articles
        )

    def _process_interviews(self, match: MatchData):
        """インタビュー記事を検索・要約"""
        for is_home in [True, False]:
            team_name = match.home_team if is_home else match.away_team
            
            # 検索
            interview_articles = self.search.search_interviews(team_name)
            
            # フィルタリング
            safe_articles = [
                a for a in interview_articles 
                if self.filter.is_safe_article(a['content'])
            ]
            
            # 要約
            if safe_articles:
                summary = self.llm.summarize_interview(team_name, safe_articles)
                summary = self.filter.check_text(summary)
            else:
                summary = f"【{team_name}】インタビュー記事が見つかりませんでした"
            
            if is_home:
                match.home_interview = summary
            else:
                match.away_interview = summary
