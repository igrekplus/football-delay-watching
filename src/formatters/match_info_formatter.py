"""
Match info formatting utilities for report generation.
"""
from src.domain.models import MatchData


class MatchInfoFormatter:
    """試合基本情報のフォーマット処理を担当するクラス"""
    
    def format_match_info_html(self, match: MatchData) -> str:
        """試合基本情報カード（大会、日時、会場）のHTMLを生成"""
        return f'''<div class="match-info-grid">
<div class="match-info-item match-info-small">
<div class="match-info-icon">🏆</div>
<div class="match-info-content">
<div class="match-info-label">大会</div>
<div class="match-info-value">{match.competition}</div>
</div>
</div>
<div class="match-info-item match-info-wide">
<div class="match-info-icon">📅</div>
<div class="match-info-content">
<div class="match-info-label">日時</div>
<div class="match-info-value">{match.kickoff_jst}<br><span class="match-info-subtext">{match.kickoff_local}</span></div>
</div>
</div>
<div class="match-info-item">
<div class="match-info-icon">🏟️</div>
<div class="match-info-content">
<div class="match-info-label">会場</div>
<div class="match-info-value">{match.venue}</div>
</div>
</div>
</div>'''

    def format_form_with_icons(self, form: str) -> str:
        """フォーム文字列（W, D, L）をアイコン付きに変換"""
        if not form:
            return ""
        icons = {"W": "✅", "D": "➖", "L": "❌"}
        icon_str = "".join(icons.get(c, c) for c in form)
        return f"{form} ({icon_str})"
