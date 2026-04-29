"""Claude (Anthropic) backend."""

import logging

from src.clients.llm_backends.base import LLMResult

logger = logging.getLogger(__name__)


class ClaudeBackend:
    """Claudeモデルへのアクセス。

    Google Search Grounding 機能はサポートしないため、`use_grounding=True` で
    呼ばれた場合は NotImplementedError を送出する。
    """

    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, model_name: str, api_key: str):
        self.name = f"claude:{model_name}"
        self.model_name = model_name
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def generate_text(
        self,
        prompt: str,
        *,
        use_grounding: bool = False,
        thinking_budget: str | None = None,
    ) -> LLMResult:
        if use_grounding:
            raise NotImplementedError(
                "ClaudeBackend does not support Google Search grounding. "
                "Route grounding-required prompts to a Gemini backend."
            )

        client = self._get_client()
        response = client.messages.create(
            model=self.model_name,
            max_tokens=self.DEFAULT_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        text_parts = []
        for block in response.content:
            block_text = getattr(block, "text", None)
            if block_text is not None:
                text_parts.append(block_text)
        text = "".join(text_parts)

        usage = None
        if getattr(response, "usage", None) is not None:
            usage = {
                "input_tokens": getattr(response.usage, "input_tokens", None),
                "output_tokens": getattr(response.usage, "output_tokens", None),
            }

        return LLMResult(
            text=text,
            grounding_metadata=None,
            backend=self.name,
            usage=usage,
        )
