"""LLM backend Protocol and result type."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LLMResult:
    """LLM呼び出し結果。

    Attributes:
        text: 生成テキスト本文
        grounding_metadata: Geminiの groundingMetadata（後段検証で利用）
        backend: 経路記録用の識別子（例: "gemini:gemini-2.5-flash"）
        usage: トークン使用量等（取得できる場合のみ）
    """

    text: str
    grounding_metadata: dict | None = None
    backend: str = ""
    usage: dict | None = None


@runtime_checkable
class LLMBackend(Protocol):
    """LLMバックエンドの共通インターフェース。"""

    name: str

    def generate_text(
        self,
        prompt: str,
        *,
        use_grounding: bool = False,
        thinking_budget: str | None = None,
    ) -> LLMResult: ...
