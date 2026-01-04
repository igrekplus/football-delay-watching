"""
Match info formatting utilities for report generation.
"""
from src.domain.models import MatchData


class MatchInfoFormatter:
    """試合基本情報のフォーマット処理を担当するクラス"""
    
    def format_match_info_html(self, match: MatchData) -> str:
        """試合基本情報カード（日時、会場）のHTMLを生成"""
        # Issue #116 Polish: 大会情報のカードを削除（ヘッダーに移動したため）
        return ""

    def format_form_with_icons(self, form: str) -> str:
        """フォーム文字列（W, D, L）をアイコン付きに変換"""
        if not form:
            return ""
        icons = {"W": "✅", "D": "➖", "L": "❌"}
        icon_str = "".join(icons.get(c, c) for c in form)
        return f"{form} ({icon_str})"
