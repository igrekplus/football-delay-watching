#!/usr/bin/env python3
"""
YouTube Data API ヘルスチェック + クエリテスト

使用方法:
    python healthcheck/check_youtube.py
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import requests

from src.youtube_service import YouTubeService
from settings.channels import get_team_channel, TACTICS_CHANNELS


@dataclass
class QuerySpec:
    category: str
    query: str
    channel_id: Optional[str]
    published_after: Optional[datetime]
    published_before: Optional[datetime]
    max_results: int


class YouTubeQueryTester:
    """実装済みの検索条件を参考に、YouTubeへクエリを投げるテスター"""

    def __init__(self, api_key: str):
        self.service = YouTubeService(api_key=api_key)

    def _build_press_conference_queries(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> List[QuerySpec]:
        channel_handle = get_team_channel(team_name)
        channel_id = self.service._resolve_channel_id(channel_handle) if channel_handle else None
        published_after = kickoff_time - timedelta(hours=self.service.RECENT_SEARCH_HOURS)
        return [
            QuerySpec(
                category="press_conference",
                query=f"{team_name} press conference",
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            ),
            QuerySpec(
                category="press_conference",
                query=f"{team_name} 記者会見",
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            ),
        ]

    def _build_historic_queries(
        self,
        home_team: str,
        away_team: str,
        kickoff_time: datetime,
    ) -> List[QuerySpec]:
        published_after = kickoff_time - timedelta(days=self.service.HISTORIC_SEARCH_DAYS)
        return [
            QuerySpec(
                category="historic",
                query=f"{home_team} vs {away_team} highlights",
                channel_id=None,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=3,
            ),
            QuerySpec(
                category="historic",
                query=f"{home_team} {away_team} extended highlights",
                channel_id=None,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=3,
            ),
        ]

    def _build_tactical_queries(
        self,
        team_name: str,
        players: List[str],
        kickoff_time: datetime,
    ) -> List[QuerySpec]:
        published_after = kickoff_time - timedelta(days=self.service.TACTICAL_SEARCH_DAYS)
        queries = []

        for handle in TACTICS_CHANNELS.values():
            channel_id = self.service._resolve_channel_id(handle)
            if not channel_id:
                continue
            queries.append(
                QuerySpec(
                    category="tactical",
                    query=f"{team_name} tactics analysis",
                    channel_id=channel_id,
                    published_after=published_after,
                    published_before=kickoff_time,
                    max_results=2,
                )
            )

        for player in players[:3]:
            queries.append(
                QuerySpec(
                    category="tactical",
                    query=f"{player} skills",
                    channel_id=None,
                    published_after=published_after,
                    published_before=kickoff_time,
                    max_results=1,
                )
            )

        return queries

    def _build_training_queries(
        self,
        team_name: str,
        kickoff_time: datetime,
    ) -> List[QuerySpec]:
        channel_handle = get_team_channel(team_name)
        channel_id = self.service._resolve_channel_id(channel_handle) if channel_handle else None
        published_after = kickoff_time - timedelta(hours=self.service.RECENT_SEARCH_HOURS)
        return [
            QuerySpec(
                category="training",
                query=f"{team_name} training",
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            ),
            QuerySpec(
                category="training",
                query=f"{team_name} 練習",
                channel_id=channel_id,
                published_after=published_after,
                published_before=kickoff_time,
                max_results=2,
            ),
        ]

    def build_queries(
        self,
        home_team: str,
        away_team: str,
        kickoff_time: datetime,
        home_players: List[str],
        away_players: List[str],
    ) -> List[QuerySpec]:
        queries: List[QuerySpec] = []
        queries.extend(self._build_press_conference_queries(home_team, kickoff_time))
        queries.extend(self._build_press_conference_queries(away_team, kickoff_time))
        queries.extend(self._build_historic_queries(home_team, away_team, kickoff_time))
        queries.extend(self._build_tactical_queries(home_team, home_players, kickoff_time))
        queries.extend(self._build_tactical_queries(away_team, away_players, kickoff_time))
        queries.extend(self._build_training_queries(home_team, kickoff_time))
        queries.extend(self._build_training_queries(away_team, kickoff_time))
        return queries

    def run_queries(self, queries: List[QuerySpec]) -> bool:
        success = True
        for i, q in enumerate(queries, 1):
            print("-" * 50)
            print(f"#{i} [{q.category}] {q.query}")
            if q.channel_id:
                print(f"  channel_id: {q.channel_id}")
            if q.published_after:
                print(f"  published_after: {q.published_after.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            if q.published_before:
                print(f"  published_before: {q.published_before.strftime('%Y-%m-%dT%H:%M:%SZ')}")
            print(f"  max_results: {q.max_results}")

            videos = self.service._search_videos(
                query=q.query,
                channel_id=q.channel_id,
                published_after=q.published_after,
                published_before=q.published_before,
                max_results=q.max_results,
            )

            if not videos:
                print("  → results: 0")
                success = False
                continue

            print(f"  → results: {len(videos)}")
            for v in videos[:3]:
                print(f"    - {v.get('title')} ({v.get('url')})")
        return success


def _extract_error_reason(resp: requests.Response) -> Optional[str]:
    try:
        data = resp.json()
        errors = data.get("error", {}).get("errors", [])
        if errors:
            return errors[0].get("reason")
    except Exception:
        return None
    return None


def check_youtube_quota(api_key: str) -> bool:
    """YouTube Data API の疎通とクォータ状態を確認"""
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": api_key,
                "q": "Premier League",
                "part": "snippet",
                "type": "video",
                "maxResults": 1,
            },
            timeout=10,
        )
    except requests.exceptions.Timeout:
        print("❌ YouTube API: タイムアウト (10秒)")
        return False
    except Exception as e:
        print(f"❌ YouTube API: エラー ({e})")
        return False

    print(f"📡 ステータスコード: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        total = data.get("pageInfo", {}).get("totalResults", "N/A")
        print(f"📈 検索結果: {total} 件")
        print("✅ YouTube API: 正常")
        print("   ⚠️ クォータはレスポンスで残量が取得できません (Cloud Consoleで確認)")
        return True

    if resp.status_code == 403:
        reason = _extract_error_reason(resp)
        if reason in {"quotaExceeded", "dailyLimitExceeded"}:
            print("⛔ YouTube API: クォータ超過")
            print("   → Cloud Consoleでクォータを確認してください")
        else:
            print("❌ YouTube API: 認証エラー")
        return False

    print(f"⚠️ YouTube API: 予期しないステータス ({resp.status_code})")
    print(f"   レスポンス: {resp.text[:200]}")
    return False


def check_youtube():
    load_dotenv()

    api_key = os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")

    print("=" * 50)
    print("📊 YouTube Data API ステータス確認")
    print("=" * 50)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    if not api_key:
        print("❌ YOUTUBE_API_KEY / GOOGLE_API_KEY が設定されていません")
        return False

    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print()

    quota_ok = check_youtube_quota(api_key)
    print()

    # 実際の検索条件に近いクエリを実行
    tester = YouTubeQueryTester(api_key=api_key)
    kickoff_time = datetime.utcnow() + timedelta(days=1)
    home_players = ["Erling Haaland", "Kevin De Bruyne", "Phil Foden"]
    away_players = ["Bukayo Saka", "Martin Odegaard", "Declan Rice"]

    queries = tester.build_queries(
        home_team="Manchester City",
        away_team="Arsenal",
        kickoff_time=kickoff_time,
        home_players=home_players,
        away_players=away_players,
    )

    print("🔍 YouTube検索クエリ実行")
    print()
    queries_ok = tester.run_queries(queries)

    return quota_ok and queries_ok


if __name__ == "__main__":
    success = check_youtube()
    print()
    print("=" * 50)
    sys.exit(0 if success else 1)
