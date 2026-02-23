import unittest
from unittest.mock import MagicMock

from src.clients.llm_client import LLMClient
from src.domain.models import MatchAggregate, MatchCore
from src.mock_provider import MockProvider
from src.news_service import NewsService


class TestIssue207MockHomeAway(unittest.TestCase):
    def setUp(self):
        self.mock_llm_client = LLMClient(use_mock=True)

    def _create_match(self) -> MatchAggregate:
        core = MatchCore(
            id="fixture-207",
            home_team="Manchester City",
            away_team="Exeter City",
            competition="FA Cup",
            kickoff_jst="2026/01/10 12:00 JST",
            kickoff_local="2026-01-10 20:00 Local",
            match_date_local="2026-01-10",
            is_target=True,
        )
        match = MatchAggregate(core=core)
        match.facts.home_manager = "Pep Guardiola"
        match.facts.away_manager = "Gary Caldwell"
        return match

    def test_llm_client_uses_home_away_key_for_interview_in_mock(self):
        home_summary = self.mock_llm_client.summarize_interview(
            "Manchester City",
            opponent_team="Exeter City",
            is_home=True,
        )
        away_summary = self.mock_llm_client.summarize_interview(
            "Exeter City",
            opponent_team="Manchester City",
            is_home=False,
        )

        self.assertEqual(
            home_summary,
            MockProvider.get_interview_summary("Manchester City", "Exeter City", True),
        )
        self.assertEqual(
            away_summary,
            MockProvider.get_interview_summary("Exeter City", "Manchester City", False),
        )
        self.assertNotEqual(home_summary, away_summary)

    def test_llm_client_uses_home_away_key_for_transfer_in_mock(self):
        home_news = self.mock_llm_client.generate_transfer_news(
            "Manchester City",
            match_date="2026-01-10",
            transfer_window_context="winter transfer window 2026",
            is_home=True,
        )
        away_news = self.mock_llm_client.generate_transfer_news(
            "Exeter City",
            match_date="2026-01-10",
            transfer_window_context="winter transfer window 2026",
            is_home=False,
        )

        self.assertEqual(
            home_news,
            MockProvider.get_transfer_news("Manchester City", "2026-01-10", True),
        )
        self.assertEqual(
            away_news,
            MockProvider.get_transfer_news("Exeter City", "2026-01-10", False),
        )
        self.assertNotEqual(home_news, away_news)

    def test_news_service_passes_is_home_to_summarize_interview(self):
        mock_llm = MagicMock()
        mock_llm.summarize_interview.side_effect = ["home interview", "away interview"]
        service = NewsService(llm_client=mock_llm)
        match = self._create_match()

        service._process_interviews(match)

        self.assertEqual(mock_llm.summarize_interview.call_count, 2)
        first_call = mock_llm.summarize_interview.call_args_list[0]
        second_call = mock_llm.summarize_interview.call_args_list[1]

        self.assertEqual(first_call.args[0], "Manchester City")
        self.assertEqual(first_call.kwargs["opponent_team"], "Exeter City")
        self.assertTrue(first_call.kwargs["is_home"])
        self.assertEqual(second_call.args[0], "Exeter City")
        self.assertEqual(second_call.kwargs["opponent_team"], "Manchester City")
        self.assertFalse(second_call.kwargs["is_home"])

    def test_news_service_passes_is_home_to_transfer_news(self):
        mock_llm = MagicMock()
        mock_llm.generate_transfer_news.side_effect = [
            "home transfer news",
            "away transfer news",
        ]
        service = NewsService(llm_client=mock_llm)
        match = self._create_match()

        service._process_transfer_news(match)

        self.assertEqual(mock_llm.generate_transfer_news.call_count, 2)
        first_call = mock_llm.generate_transfer_news.call_args_list[0]
        second_call = mock_llm.generate_transfer_news.call_args_list[1]

        self.assertEqual(first_call.args[0], "Manchester City")
        self.assertTrue(first_call.kwargs["is_home"])
        self.assertEqual(second_call.args[0], "Exeter City")
        self.assertFalse(second_call.kwargs["is_home"])


if __name__ == "__main__":
    unittest.main()
