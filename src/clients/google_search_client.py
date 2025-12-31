"""
Google Custom Search クライアント

Google Custom Search APIとのやり取りを一元化し、モック対応もここで行う。
ServiceはこのClientを通じて検索機能を使用する。
"""

import logging
from typing import Dict, List

import requests

from config import config
from settings.search_specs import (
    GOOGLE_SEARCH_SPECS,
    build_google_query,
    get_google_search_params,
)
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class GoogleSearchClient:
    """Google Custom Search APIクライアント"""
    
    API_URL = "https://www.googleapis.com/customsearch/v1"
    
    def __init__(
        self, 
        api_key: str = None, 
        engine_id: str = None,
        use_mock: bool = None
    ):
        """
        Args:
            api_key: Google Search API Key
            engine_id: Custom Search Engine ID
            use_mock: モックモード
        """
        self.api_key = api_key or config.GOOGLE_SEARCH_API_KEY
        self.engine_id = engine_id or config.GOOGLE_SEARCH_ENGINE_ID
        self.use_mock = use_mock if use_mock is not None else config.USE_MOCK_DATA
    
    def search(
        self, 
        query: str, 
        num: int = 10,
        date_restrict: str = "d2",
        gl: str = "us"
    ) -> List[Dict]:
        """
        汎用検索
        
        Args:
            query: 検索クエリ
            num: 取得件数
            date_restrict: 日付制限（例: "d2"=2日以内）
            gl: 地域コード
            
        Returns:
            検索結果リスト
        """
        params = {
            "key": self.api_key,
            "cx": self.engine_id,
            "q": query,
            "dateRestrict": date_restrict,
            "gl": gl,
            "num": num
        }
        
        try:
            response = requests.get(self.API_URL, params=params)
            data = response.json()
            items = data.get('items', [])
            # API呼び出しを記録
            ApiStats.record_call("Google Custom Search")
            return items
        except Exception as e:
            logger.error(f"Google Search error: {e}")
            return []
    
    def search_news(
        self, 
        home_team: str, 
        away_team: str,
        competition: str = ""
    ) -> List[Dict[str, str]]:
        """
        試合関連のニュース記事を検索
        
        Args:
            home_team: ホームチーム名
            away_team: アウェイチーム名
            competition: 大会名
            
        Returns:
            記事リスト（content, title, source, url, relevance_score）
        """
        if self.use_mock:
            return self._get_mock_news(home_team, away_team)
        
        # スペックからクエリを生成
        query = build_google_query("news", home_team=home_team, away_team=away_team)
        
        # スペックから検索パラメータを取得
        spec = GOOGLE_SEARCH_SPECS["news"]
        gl = spec["gl_japan"] if "Japan" in competition else spec["gl_default"]
        
        items = self.search(
            query=query,
            num=config.NEWS_SEARCH_LIMIT,
            date_restrict=spec["date_restrict"],
            gl=gl
        )
        
        if not items:
            logger.warning(f"No headlines found for {home_team} vs {away_team}")
            return []
        
        articles = []
        for item in items:
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            link = item.get('link', '')
            display_link = item.get('displayLink', 'Unknown Source')
            
            content_text = f"{title}\n{snippet}"
            
            # Issue #34: 両チーム名を含むかスコアを計算
            content_lower = content_text.lower()
            relevance_score = 0
            if home_team.lower() in content_lower:
                relevance_score += 1
            if away_team.lower() in content_lower:
                relevance_score += 1
            
            articles.append({
                "content": content_text,
                "title": title,
                "source": display_link,
                "url": link,
                "relevance_score": relevance_score
            })
            logger.info(f"  [SEARCH] {title} ({display_link}) relevance={relevance_score}")
        
        # Issue #34: 両チーム名を含む記事を優先してソート
        articles.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return articles
    
    def search_interviews(self, team_name: str) -> List[Dict[str, str]]:
        """
        監督・選手インタビュー記事を検索
        
        Returns:
            記事リスト（content, title, source）
        """
        if self.use_mock:
            return []  # モック時はインタビュー記事なし
        
        # スペックからクエリ・パラメータを生成
        search_types = ["interview_manager", "interview_player"]
        
        all_articles = []
        
        for search_type in search_types:
            query = build_google_query(search_type, team_name=team_name)
            params = get_google_search_params(search_type)
            
            items = self.search(
                query=query,
                num=params["num"],
                date_restrict=params["date_restrict"],
                gl=params["gl"]
            )
            
            if not items:
                logger.info(f"  [INTERVIEW] {team_name}: 検索結果なし (query: {query[:50]}...)")
                continue
            
            for item in items:
                title = item.get('title', '')
                snippet = item.get('snippet', '')
                content_text = f"{title}\n{snippet}"
                
                all_articles.append({
                    "content": content_text,
                    "title": title,
                    "source": item.get('displayLink', 'Unknown')
                })
                logger.info(f"  [INTERVIEW] {title}")
        
        if not all_articles:
            logger.info(f"  [INTERVIEW] {team_name}: 関連記事が見つかりませんでした")
        
        return all_articles[:4]  # Max 4 articles per team
    
    # ========== モック用メソッド ==========
    
    def _get_mock_news(self, home_team: str, away_team: str) -> List[Dict[str, str]]:
        from src.mock_provider import MockProvider
        return MockProvider.get_news(home_team, away_team)

