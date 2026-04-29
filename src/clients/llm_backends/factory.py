"""Backend factory: 設定値 (`gemini-flash` / `gemini-pro` / `claude-sonnet` /
`claude-haiku`) を具体的な LLMBackend に解決する。"""

from __future__ import annotations

from config import config
from src.clients.llm_backends.base import LLMBackend

_BACKEND_CACHE: dict[str, LLMBackend] = {}


def get_backend(backend_id: str) -> LLMBackend:
    """backend_id から LLMBackend インスタンスを取得（プロセス内でキャッシュ）。"""
    if backend_id in _BACKEND_CACHE:
        return _BACKEND_CACHE[backend_id]

    if backend_id in ("gemini-flash", "gemini-pro"):
        from src.clients.llm_backends.gemini_backend import GeminiBackend

        model_name = (
            config.GEMINI_PRO_MODEL
            if backend_id == "gemini-pro"
            else config.GEMINI_FLASH_MODEL
        )
        backend = GeminiBackend(model_name=model_name, api_key=config.GOOGLE_API_KEY)
    elif backend_id in ("claude-sonnet", "claude-haiku"):
        from src.clients.llm_backends.claude_backend import ClaudeBackend

        model_name = (
            config.CLAUDE_SONNET_MODEL
            if backend_id == "claude-sonnet"
            else config.CLAUDE_HAIKU_MODEL
        )
        backend = ClaudeBackend(model_name=model_name, api_key=config.ANTHROPIC_API_KEY)
    else:
        raise ValueError(f"Unknown backend id: {backend_id!r}")

    _BACKEND_CACHE[backend_id] = backend
    return backend


def reset_backend_cache() -> None:
    """テスト用: バックエンドキャッシュをクリア。"""
    _BACKEND_CACHE.clear()
