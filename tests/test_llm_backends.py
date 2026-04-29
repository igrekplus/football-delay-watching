"""Backend factory / Gemini / Claude のユニットテスト。

実際のSDKを起動せず、内部のクライアント呼び出し部分のみmockする。
"""

import unittest
from unittest.mock import MagicMock, patch

from src.clients.llm_backends import (
    LLMResult,
    get_backend,
    reset_backend_cache,
)
from src.clients.llm_backends.claude_backend import ClaudeBackend
from src.clients.llm_backends.gemini_backend import GeminiBackend


class TestBackendFactory(unittest.TestCase):
    def setUp(self):
        reset_backend_cache()

    def tearDown(self):
        reset_backend_cache()

    @patch("src.clients.llm_backends.factory.config")
    def test_resolves_gemini_flash(self, mock_config):
        mock_config.GOOGLE_API_KEY = "fake"
        mock_config.GEMINI_FLASH_MODEL = "gemini-2.5-flash"
        backend = get_backend("gemini-flash")
        self.assertIsInstance(backend, GeminiBackend)
        self.assertEqual(backend.model_name, "gemini-2.5-flash")
        self.assertIn("gemini-2.5-flash", backend.name)

    @patch("src.clients.llm_backends.factory.config")
    def test_resolves_gemini_pro(self, mock_config):
        mock_config.GOOGLE_API_KEY = "fake"
        mock_config.GEMINI_PRO_MODEL = "gemini-2.5-pro"
        backend = get_backend("gemini-pro")
        self.assertIsInstance(backend, GeminiBackend)
        self.assertEqual(backend.model_name, "gemini-2.5-pro")

    @patch("src.clients.llm_backends.factory.config")
    def test_resolves_claude_sonnet(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "fake"
        mock_config.CLAUDE_SONNET_MODEL = "claude-sonnet-4-6"
        backend = get_backend("claude-sonnet")
        self.assertIsInstance(backend, ClaudeBackend)
        self.assertEqual(backend.model_name, "claude-sonnet-4-6")

    @patch("src.clients.llm_backends.factory.config")
    def test_resolves_claude_haiku(self, mock_config):
        mock_config.ANTHROPIC_API_KEY = "fake"
        mock_config.CLAUDE_HAIKU_MODEL = "claude-haiku-4-5-20251001"
        backend = get_backend("claude-haiku")
        self.assertIsInstance(backend, ClaudeBackend)

    def test_unknown_backend_raises(self):
        with self.assertRaises(ValueError):
            get_backend("invalid-id")

    @patch("src.clients.llm_backends.factory.config")
    def test_caches_backend_instances(self, mock_config):
        mock_config.GOOGLE_API_KEY = "fake"
        mock_config.GEMINI_FLASH_MODEL = "gemini-2.5-flash"
        a = get_backend("gemini-flash")
        b = get_backend("gemini-flash")
        self.assertIs(a, b)


class TestGeminiBackend(unittest.TestCase):
    def test_plain_returns_result(self):
        backend = GeminiBackend(model_name="gemini-2.5-flash", api_key="fake")
        fake_response = MagicMock()
        fake_response.text = "hello"
        fake_model = MagicMock()
        fake_model.generate_content.return_value = fake_response
        backend._sdk_model = fake_model

        result = backend.generate_text("prompt", use_grounding=False)
        self.assertIsInstance(result, LLMResult)
        self.assertEqual(result.text, "hello")
        self.assertIsNone(result.grounding_metadata)
        self.assertIn("gemini-2.5-flash", result.backend)
        fake_model.generate_content.assert_called_once_with("prompt")

    @patch("src.clients.gemini_rest_client.GeminiRestClient")
    def test_grounding_uses_rest_client(self, mock_rest_cls):
        mock_rest = MagicMock()
        mock_rest.generate_content_with_grounding.return_value = "grounded text"
        mock_rest_cls.return_value = mock_rest

        backend = GeminiBackend(model_name="gemini-2.5-pro", api_key="fake")
        result = backend.generate_text("prompt", use_grounding=True)

        self.assertEqual(result.text, "grounded text")
        mock_rest_cls.assert_called_once_with(
            api_key="fake", model_name="gemini-2.5-pro"
        )
        mock_rest.generate_content_with_grounding.assert_called_once_with("prompt")


class TestClaudeBackend(unittest.TestCase):
    def test_grounding_raises(self):
        backend = ClaudeBackend(model_name="claude-sonnet-4-6", api_key="fake")
        with self.assertRaises(NotImplementedError):
            backend.generate_text("prompt", use_grounding=True)

    def test_plain_returns_concatenated_text(self):
        backend = ClaudeBackend(model_name="claude-sonnet-4-6", api_key="fake")

        block1 = MagicMock()
        block1.text = "Hello "
        block2 = MagicMock()
        block2.text = "world"

        usage = MagicMock()
        usage.input_tokens = 10
        usage.output_tokens = 20

        fake_response = MagicMock()
        fake_response.content = [block1, block2]
        fake_response.usage = usage

        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_response
        backend._client = fake_client

        result = backend.generate_text("prompt", use_grounding=False)
        self.assertEqual(result.text, "Hello world")
        self.assertIn("claude-sonnet-4-6", result.backend)
        self.assertEqual(result.usage, {"input_tokens": 10, "output_tokens": 20})
        fake_client.messages.create.assert_called_once()
        kwargs = fake_client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "claude-sonnet-4-6")
        self.assertEqual(kwargs["messages"], [{"role": "user", "content": "prompt"}])


if __name__ == "__main__":
    unittest.main()
