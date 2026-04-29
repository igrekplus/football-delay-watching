"""
LLM Backend abstraction layer.

Resolves prompt-level backend selection (gemini-flash / gemini-pro /
claude-sonnet / claude-haiku) declared in `settings.gemini_prompts.PROMPT_METADATA`
into concrete model clients.
"""

from src.clients.llm_backends.base import LLMBackend, LLMResult
from src.clients.llm_backends.factory import get_backend, reset_backend_cache

__all__ = ["LLMBackend", "LLMResult", "get_backend", "reset_backend_cache"]
