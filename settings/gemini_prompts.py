"""
Geminiプロンプト設定

LLMClient用のプロンプトテンプレートを集約。
テンプレートは settings/prompts/ 以下のMarkdownファイルから読み込み。

Issue #120: LLMプロンプトの外部設定化（疎結合化）
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# プロンプトファイルのディレクトリ
PROMPTS_DIR = Path(__file__).parent / "prompts"


# =============================================================================
# プロンプトメタデータ
#
# 各プロンプトの設定（ラベル、文字数制限、Grounding使用有無等）
# テンプレート本文は prompts/ ディレクトリのMarkdownファイルから読み込む
# =============================================================================

PROMPT_METADATA: Dict[str, Dict[str, Any]] = {
    "news_summary": {
        "label": "ニュースサマリー",
        "char_limit": (600, 1000),
        "use_grounding": True,
    },

    "tactical_preview": {
        "label": "戦術プレビュー",
        "use_grounding": True,
    },

    "check_spoiler": {
        "label": "ネタバレ判定",
        "text_limit": 1500,
        "use_grounding": False,
    },

    "interview": {
        "label": "インタビュー要約",
        "char_limit": (1500, 2000),
        "use_grounding": True,
    },

    "same_country_trivia": {
        "label": "同国対決トリビア",
        "char_limit_per_country": (50, 150),
        "use_grounding": False,
    },

    "former_club_trivia": {
        "label": "古巣対決トリビア",
        "char_limit": (100, 300),  # 最大3件×80字+余白
        "use_grounding": True,  # リアルタイム検索で確定
    },
}


# =============================================================================
# テンプレートキャッシュ
# =============================================================================

_template_cache: Dict[str, str] = {}


def _load_template(prompt_type: str) -> str:
    """
    Markdownファイルからテンプレートを読み込む（キャッシュ付き）
    
    Args:
        prompt_type: プロンプト種別
        
    Returns:
        テンプレート文字列
        
    Raises:
        FileNotFoundError: テンプレートファイルが見つからない場合
    """
    if prompt_type in _template_cache:
        return _template_cache[prompt_type]
    
    file_path = PROMPTS_DIR / f"{prompt_type}.md"
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {file_path}")
    
    template = file_path.read_text(encoding="utf-8")
    _template_cache[prompt_type] = template
    return template


def clear_template_cache():
    """テンプレートキャッシュをクリア（開発・テスト用）"""
    _template_cache.clear()


# =============================================================================
# ヘルパー関数
# =============================================================================

def build_prompt(
    prompt_type: str,
    **kwargs
) -> str:
    """
    プロンプトスペックからプロンプト文字列を生成

    Args:
        prompt_type: プロンプト種別（news_summary, tactical_preview等）
        **kwargs: テンプレート変数

    Returns:
        プロンプト文字列
    
    Raises:
        ValueError: 不明なプロンプト種別
        FileNotFoundError: テンプレートファイルが見つからない場合
    """
    if prompt_type not in PROMPT_METADATA:
        raise ValueError(f"Unknown prompt type: {prompt_type}")

    template = _load_template(prompt_type)
    return template.format(**kwargs)


def get_prompt_config(prompt_type: str) -> Dict[str, Any]:
    """
    プロンプト種別の設定を取得

    Args:
        prompt_type: プロンプト種別

    Returns:
        設定辞書（char_limit, use_grounding等）
    
    Raises:
        ValueError: 不明なプロンプト種別
    """
    spec = PROMPT_METADATA.get(prompt_type)
    if not spec:
        raise ValueError(f"Unknown prompt type: {prompt_type}")

    return {
        "label": spec.get("label", prompt_type),
        "char_limit": spec.get("char_limit"),
        "char_limit_per_country": spec.get("char_limit_per_country"),
        "text_limit": spec.get("text_limit"),
        "use_grounding": spec.get("use_grounding", False),
    }


def get_char_limit(prompt_type: str) -> Optional[Tuple[int, int]]:
    """
    プロンプト種別の文字数制限を取得

    Args:
        prompt_type: プロンプト種別

    Returns:
        (最小, 最大) または None
    """
    config = get_prompt_config(prompt_type)
    return config.get("char_limit")


def uses_grounding(prompt_type: str) -> bool:
    """
    プロンプトがGrounding機能を使用するか判定

    Args:
        prompt_type: プロンプト種別

    Returns:
        Grounding使用の場合True
    """
    config = get_prompt_config(prompt_type)
    return config.get("use_grounding", False)


def list_prompt_types() -> list:
    """
    利用可能なプロンプト種別の一覧を取得
    
    Returns:
        プロンプト種別のリスト
    """
    return list(PROMPT_METADATA.keys())
