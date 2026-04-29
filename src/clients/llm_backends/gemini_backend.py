"""Gemini backend: SDK for non-grounding, REST for grounding."""

import logging

from src.clients.llm_backends.base import LLMResult

logger = logging.getLogger(__name__)


class GeminiBackend:
    """Geminiモデルへのアクセス。

    非Grounding時は `google-generativeai` SDK、Grounding時は GeminiRestClient
    （`googleSearch` tool 指定）を経由する。
    """

    def __init__(self, model_name: str, api_key: str):
        self.name = f"gemini:{model_name}"
        self.model_name = model_name
        self.api_key = api_key
        self._sdk_model = None

    def _get_sdk_model(self):
        if self._sdk_model is None:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._sdk_model = genai.GenerativeModel(self.model_name)
        return self._sdk_model

    def generate_text(
        self,
        prompt: str,
        *,
        use_grounding: bool = False,
        thinking_budget: str | None = None,
    ) -> LLMResult:
        if use_grounding:
            return self._generate_with_grounding(prompt, thinking_budget)
        return self._generate_plain(prompt, thinking_budget)

    def _generate_plain(self, prompt: str, thinking_budget: str | None) -> LLMResult:
        model = self._get_sdk_model()
        response = model.generate_content(prompt)
        return LLMResult(
            text=response.text,
            grounding_metadata=None,
            backend=self.name,
        )

    def _generate_with_grounding(
        self, prompt: str, thinking_budget: str | None
    ) -> LLMResult:
        from src.clients.gemini_rest_client import GeminiRestClient

        rest_client = GeminiRestClient(api_key=self.api_key, model_name=self.model_name)
        text = rest_client.generate_content_with_grounding(prompt)
        return LLMResult(
            text=text,
            grounding_metadata=None,
            backend=self.name,
        )
