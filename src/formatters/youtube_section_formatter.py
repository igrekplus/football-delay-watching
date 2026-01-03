"""
YouTube section formatting utilities for report generation.
"""
from typing import List, Dict
from src.utils.datetime_util import DateTimeUtil


class YouTubeSectionFormatter:
    """YouTube動画セクションのフォーマット処理を担当するクラス"""
    
    # カテゴリラベル定義
    CATEGORY_LABELS = {
        "press_conference": "🎤 記者会見",
        "historic": "⚔️ 因縁",
        "tactical": "📊 戦術分析",
        "player_highlight": "⭐ 選手紹介",
        "training": "🏃 練習風景",
    }

    def __init__(self):
        pass

    def format_youtube_section(self, video_data: Dict, match_key: str) -> str:
        """YouTube動画セクション全体のHTML/Markdownを生成"""
        # 新形式（{kept, removed, overflow}）と旧形式（リスト）の両方に対応
        if isinstance(video_data, dict):
            videos = video_data.get("kept", [])
            removed_videos = video_data.get("removed", [])
            overflow_videos = video_data.get("overflow", [])
        else:
            videos = video_data  # 旧形式（リスト）
            removed_videos = []
            overflow_videos = []
        
        if not (videos or removed_videos or overflow_videos):
            return ""

        lines = ["### ■ 📹 試合前の見どころ動画", ""]
        
        for cat_key, cat_label in self.CATEGORY_LABELS.items():
            cat_videos = [v for v in videos if v.get("category") == cat_key]
            cat_overflow = [v for v in overflow_videos if v.get("category") == cat_key]
            cat_removed = [v for v in removed_videos if v.get("category") == cat_key]
            
            if cat_videos or cat_overflow or cat_removed:
                # メインセクション（表示件数）
                lines.append(f"<details open>")
                lines.append(f"<summary><strong>{cat_label} ({len(cat_videos)}件)</strong></summary>")
                
                if cat_videos:
                    lines.extend(self.render_video_table(cat_videos))
                else:
                    lines.append("<p>表示する動画がありません</p>")
                
                # ソート落ち動画（overflow）の折りたたみ（サムネイルなし）
                if cat_overflow:
                    lines.append(f"<details>")
                    lines.append(f"<summary>📋 ソートで落ちた動画 ({len(cat_overflow)}件)</summary>")
                    lines.extend(self.render_video_table(cat_overflow, show_thumbnail=False))
                    lines.append("</details>")
                
                # 除外動画（removed）の折りたたみ（サムネイルなし、理由付き）
                if cat_removed:
                    lines.append(f"<details>")
                    lines.append(f"<summary>🚫 除外された動画 ({len(cat_removed)}件)</summary>")
                    lines.extend(self.render_video_table(cat_removed, show_reason=True, show_thumbnail=False))
                    lines.append("</details>")
                
                lines.append("</details>")
                lines.append("")
        
        return "\n".join(lines)

    def render_video_table(self, video_list: list, show_reason: bool = False, show_thumbnail: bool = True) -> list:
        """動画リストをグリッドまたはリスト形式のHTMLに変換"""
        grid_lines = []
        
        if show_thumbnail:
            # サムネイル付きグリッド（メイン表示用）
            grid_lines.append('<div class="youtube-grid">')
            
            for v in video_list:
                title = v.get('title', 'No Title')
                url = v.get('url', '')
                thumbnail = v.get('thumbnail_url', '')
                channel_display = v.get('channel_display', v.get('channel_name', 'Unknown'))
                published_at = v.get('published_at', '')
                query_label = v.get('query_label', '')
                filter_reason = v.get('filter_reason', '') if show_reason else ''
                
                relative_date = DateTimeUtil.format_relative_date(published_at)
                
                # カード形式で表示
                label_badge = f'<span class="youtube-card-label">{query_label}</span>' if query_label else ''
                reason_badge = f'<span class="youtube-card-reason">除外: {filter_reason}</span>' if filter_reason else ''
                
                card_html = f'''<div class="youtube-card">
    <a href="{url}" target="_blank" class="youtube-card-thumbnail">
        <img src="{thumbnail}" alt="thumbnail">
    </a>
    <div class="youtube-card-content">
        {label_badge}{reason_badge}
        <div class="youtube-card-title">
            <a href="{url}" target="_blank">{title}</a>
        </div>
        <div class="youtube-card-meta">
            <span class="youtube-card-channel">📺 {channel_display}</span>
            <span class="youtube-card-date">🕐 {relative_date}</span>
        </div>
    </div>
</div>'''
                grid_lines.append(card_html)
            
            grid_lines.append('</div>')
        else:
            # サムネイルなしリスト（ソート落ち/除外用）
            grid_lines.append('<ul style="font-size:0.85em;margin:0;padding-left:1.5em;">')
            for v in video_list:
                title = v.get('title', 'No Title')
                if len(title) > 50:
                    title = title[:47] + "..."
                url = v.get('url', '')
                channel = v.get('channel_name', 'Unknown')
                query_label = v.get('query_label', '')
                filter_reason = v.get('filter_reason', '') if show_reason else ''
                
                label_prefix = f'【{query_label}】 ' if query_label else ''
                reason_suffix = f' <span style="color:#f44336">[{filter_reason}]</span>' if filter_reason else ''
                grid_lines.append(f'<li><a href="{url}" target="_blank">{label_prefix}{title}</a> - {channel}{reason_suffix}</li>')
            grid_lines.append('</ul>')
        
        return grid_lines
