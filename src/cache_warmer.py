"""
キャッシュウォーミングモジュール

試合がない日に上位チームの選手データをGCSにプリフェッチし、
週末の試合レポート生成時にキャッシュHITさせることでAPI消費を削減する。
"""

import logging

from config import config
from settings.cache_config import CACHE_BACKEND
from src.clients.api_football_client import ApiFootballClient
from src.utils.execution_policy import ExecutionPolicy

logger = logging.getLogger(__name__)


class CacheWarmer:
    """上位チームの選手データをキャッシュするクラス"""

    def __init__(self):
        self.client = ApiFootballClient()
        self.policy = ExecutionPolicy()

    def run(self, remaining_quota: int) -> dict:
        """
        キャッシュウォーミングを実行

        Args:
            remaining_quota: 残りAPIクォータ

        Returns:
            実行結果の統計情報
        """
        # Initial Check
        if not self.policy.should_continue(remaining_quota):
            return {"skipped": True, "reason": "limit_reached_at_start"}

        logger.info(f"Starting cache warming with {remaining_quota} remaining quota")

        # EPLとCLのチームを統合（重複除去）
        all_teams: set[tuple] = set()
        all_teams.update(config.EPL_CACHE_TEAMS)
        all_teams.update(config.CL_CACHE_TEAMS)

        logger.info(f"Target teams: {len(all_teams)} unique teams")

        players_processed = 0
        available_quota = remaining_quota - config.CACHE_WARMING_QUOTA_THRESHOLD

        for team_id, team_name in all_teams:
            if not self.policy.should_continue(available_quota):
                break

            logger.info(f"Processing team: {team_name} (ID: {team_id})")

            # スクワッド取得
            squad = self.client.get_squad(team_id, team_name)

            # クォータは保守的に減算（キャッシュHIT時も減算）
            # 実際のAPI呼び出しカウントはApiStatsで追跡
            available_quota -= 1

            if not squad:
                logger.warning(f"No squad data for {team_name}")
                continue

            # 各選手をキャッシュ
            for player in squad:
                if not self.policy.should_continue(available_quota):
                    break

                player_id = player.get("id")
                if player_id:
                    result = self.client.get_player(player_id, 2024, team_name)
                    available_quota -= 1
                    if result:
                        players_processed += 1

        result = {
            "skipped": False,
            "teams_processed": len(all_teams),
            "players_processed": players_processed,
            # requests_made は ApiStats で追跡（cache_warmer独自のカウントは廃止）
        }

        logger.info(f"Cache warming completed: {result}")
        return result


def run_cache_warming(remaining_quota: int) -> dict:
    """キャッシュウォーミングを実行するエントリーポイント"""
    import os

    # Check if cache warming is enabled via environment variable
    cache_warming_enabled = (
        os.getenv("CACHE_WARMING_ENABLED", "False").lower() == "true"
    )
    if not cache_warming_enabled:
        logger.info("Cache warming skipped: CACHE_WARMING_ENABLED is False")
        return {"skipped": True, "reason": "disabled"}

    if config.USE_MOCK_DATA:
        logger.info("Cache warming skipped: mock mode")
        return {"skipped": True, "reason": "mock_mode"}

    if CACHE_BACKEND != "gcs":
        logger.info("Cache warming skipped: GCS backend not enabled")
        return {"skipped": True, "reason": "no_gcs"}

    warmer = CacheWarmer()
    return warmer.run(remaining_quota)
