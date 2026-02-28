import unittest
from unittest.mock import MagicMock, patch

from src.clients.llm_client import LLMClient


class TestLLMResponseLogging(unittest.TestCase):
    def setUp(self):
        self.mock_cache_store = MagicMock()
        # ApiStats.record_call, ApiStats.record_cache_hit をモック化する必要がある
        with (
            patch(
                "src.clients.llm_client.create_cache_store",
                return_value=self.mock_cache_store,
            ),
            patch("src.clients.llm_client.config") as mock_config,
        ):
            mock_config.GOOGLE_API_KEY = "fake_key"
            mock_config.USE_MOCK_DATA = False
            self.client = LLMClient()

    @patch("src.clients.llm_client.logger")
    def test_log_llm_response_with_source_api(self, mock_logger):
        """source=api でログヘッダーに source=api が含まれること"""
        self.client._log_llm_response("test_type", "test_response", source="api")

        # 3回のlogger.info呼び出しを期待
        self.assertEqual(mock_logger.info.call_count, 3)
        header_call = mock_logger.info.call_args_list[0]
        self.assertIn("source=api", header_call[0][0])
        self.assertIn("[test_type]", header_call[0][0])

    @patch("src.clients.llm_client.logger")
    def test_log_llm_response_with_source_cache(self, mock_logger):
        """source=cache でログヘッダーに source=cache が含まれること"""
        self.client._log_llm_response("test_type", "test_response", source="cache")

        header_call = mock_logger.info.call_args_list[0]
        self.assertIn("source=cache", header_call[0][0])

    @patch("src.clients.llm_client.logger")
    def test_log_llm_request_logs_prompt_type_and_params(self, mock_logger):
        """_log_llm_request が prompt_type と params をログに出力すること"""
        self.client._log_llm_request("test_type", "test_prompt", home="LIV", away="ARS")

        header_call = mock_logger.info.call_args_list[0]
        self.assertIn("[test_type]", header_call[0][0])
        self.assertIn("home=LIV", header_call[0][0])
        self.assertIn("away=ARS", header_call[0][0])

        content_call = mock_logger.info.call_args_list[1]
        self.assertIn("test_prompt", content_call[0][0])

    @patch("src.clients.llm_client.logger")
    def test_log_llm_request_truncates_long_prompt(self, mock_logger):
        """長いプロンプトが truncate されること"""
        long_prompt = "A" * 1000
        self.client._log_llm_request("test_type", long_prompt, max_chars=100)

        content_call = mock_logger.info.call_args_list[1]
        self.assertTrue(content_call[0][0].endswith("..."))
        self.assertIn("(1000 chars)", content_call[0][0])

    @patch("src.clients.llm_client.ApiStats")
    @patch("src.clients.llm_client.logger")
    def test_cache_hit_logs_response(self, mock_logger, mock_api_stats):
        """キャッシュヒット時に _log_llm_response が source=cache で呼び出されること"""
        cache_key = "grounding/test/h_vs_a.json"
        # TTL = 7日のキャッシュ。現在時刻を固定することで期限切れを防ぐ
        data = {"timestamp": "2026-02-15T18:00:00", "content": "cached_content"}
        self.mock_cache_store.read.return_value = data

        from datetime import datetime

        fixed_now = datetime(2026, 2, 16, 0, 0, 0)  # timestamp の翌日 = age_days=0

        with patch("src.clients.llm_client.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = fixed_now

            with patch.object(self.client, "_log_llm_response") as mock_log_resp:
                content = self.client._read_grounding_cache(cache_key, "test")

                self.assertEqual(content, "cached_content")
                mock_log_resp.assert_called_once_with(
                    "test", "cached_content", source="cache"
                )

    @patch("src.clients.llm_client.LLMClient.generate_content")
    @patch("src.clients.llm_client.logger")
    def test_check_spoiler_logs_raw_response(self, mock_logger, mock_gen):
        """check_spoiler でパース前応答がログに出ること"""
        mock_gen.return_value = '{"is_safe": true, "reason": "ok"}'

        with patch.object(self.client, "_log_llm_response") as mock_log_resp:
            self.client.check_spoiler("text", "home", "away")

            # _log_llm_response が呼び出されたか（ヘッダーと中身の検証は _log_llm_response 自体のテストで済ませている）
            self.assertTrue(
                any(
                    call.args[0] == "check_spoiler"
                    for call in mock_log_resp.call_args_list
                )
            )

    @patch("src.clients.llm_client.LLMClient.generate_content")
    @patch("src.clients.llm_client.logger")
    def test_fact_check_logs_raw_response(self, mock_logger, mock_gen):
        """fact_check_former_club_batch でパース前応答がログに出ること"""
        mock_gen.return_value = (
            '[{"player_name": "P1", "is_valid": true, "reason": "ok"}]'
        )
        entries = [
            {
                "player_name": "P1",
                "current_team": "T1",
                "opponent_team": "T2",
                "description": "desc",
            }
        ]

        with patch.object(self.client, "_log_llm_response") as mock_log_resp:
            self.client.fact_check_former_club_batch(entries, "home", "away")

            self.assertTrue(
                any(
                    call.args[0] == "former_club_fact_check"
                    for call in mock_log_resp.call_args_list
                )
            )


if __name__ == "__main__":
    unittest.main()
