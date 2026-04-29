import unittest
from unittest.mock import MagicMock, patch

from config import config
from src.domain.models import MatchAggregate, MatchCore
from src.news_service import NewsService


class TestTransferFlag(unittest.TestCase):
    def setUp(self):
        # 元の設定を保存
        self.original_flag = config.ENABLE_TRANSFER_NEWS

    def tearDown(self):
        # 設定を元に戻す
        config.ENABLE_TRANSFER_NEWS = self.original_flag

    def _create_mock_match(self):
        core = MatchCore(
            id="test-123",
            home_team="Arsenal",
            away_team="Chelsea",
            competition="EPL",
            kickoff_jst="2026/02/14 20:00 JST",
            kickoff_local="2026-02-14 11:00 Local",
            is_target=True,
        )
        match = MatchAggregate(core=core)
        return match

    def test_news_service_skips_transfer_when_disabled(self):
        """フラグがFalseの時、_process_transfer_newsが呼ばれないこと"""
        config.ENABLE_TRANSFER_NEWS = False

        # Mock LLM Client
        mock_llm = MagicMock()
        mock_llm.check_spoiler.return_value = (True, "")  # 追加
        service = NewsService(llm_client=mock_llm)

        # Mock MatchAggregate
        match = self._create_mock_match()

        with (
            patch.object(service, "_generate_summary", return_value="summary"),
            patch.object(
                service, "_generate_tactical_preview", return_value="tactical"
            ),
            patch.object(service, "_process_interviews"),
            patch.object(service, "_process_transfer_news") as mock_transfer,
        ):
            service.process_news([match])

            # 呼ばれていないことを確認
            mock_transfer.assert_not_called()

    def test_news_service_calls_transfer_when_enabled(self):
        """フラグがTrueの時、_process_transfer_newsが呼ばれること"""
        config.ENABLE_TRANSFER_NEWS = True

        # Mock LLM Client
        mock_llm = MagicMock()
        mock_llm.check_spoiler.return_value = (True, "")  # 追加
        service = NewsService(llm_client=mock_llm)

        # Mock MatchAggregate
        match = self._create_mock_match()

        with (
            patch.object(service, "_generate_summary", return_value="summary"),
            patch.object(
                service, "_generate_tactical_preview", return_value="tactical"
            ),
            patch.object(service, "_process_interviews"),
            patch.object(service, "_process_transfer_news") as mock_transfer,
        ):
            service.process_news([match])

            # 呼ばれていることを確認
            mock_transfer.assert_called_once_with(match)

    def test_news_service_hides_spoiler_summary_when_detected(self):
        """スポイラー判定時、理由や本文をレポート本文へ出さないこと"""
        config.ENABLE_TRANSFER_NEWS = False

        mock_llm = MagicMock()
        mock_llm.check_spoiler.return_value = (
            False,
            "PSGが勝利したため",
        )
        service = NewsService(llm_client=mock_llm)
        match = self._create_mock_match()

        with (
            patch.object(
                service,
                "_generate_summary",
                return_value="PSGが勝利した。合計9ゴール。",
            ),
            patch.object(
                service,
                "_generate_tactical_preview",
                return_value="tactical",
            ),
            patch.object(service, "_process_interviews"),
        ):
            service.process_news([match])

        self.assertEqual(
            match.preview.news_summary,
            "試合結果に触れる可能性があるため、ニュース要約の表示を控えています。",
        )
        self.assertNotIn("PSGが勝利", match.preview.news_summary)
        self.assertNotIn("合計9ゴール", match.preview.news_summary)


if __name__ == "__main__":
    unittest.main()
