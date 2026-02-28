"""
YouTube section formatting utilities for report generation.
"""

from src.utils.datetime_util import DateTimeUtil


class YouTubeSectionFormatter:
    """YouTube動画セクションのフォーマット処理を担当するクラス"""

    # カテゴリラベル定義
    CATEGORY_LABELS = {
        "tactical": "📊 戦術分析",
        "historic": "🎬 過去ハイライト",
        "player_highlight": "⭐ 選手紹介",
        "press_conference": "🎤 記者会見",
        "training": "🏃 練習風景",
    }

    def __init__(self):
        pass

    def format_youtube_section(self, video_data: dict, match_key: str) -> str:
        """YouTube動画セクション全体のHTML/Markdownを生成"""
        # 新形式（{kept, removed, overflow}）と旧形式（リスト）の両方に対応
        if isinstance(video_data, dict):
            videos = video_data.get("kept", [])
        else:
            videos = video_data  # 旧形式（リスト）

        if not videos:
            return ""

        lines = ["<h3>■ 📹 試合前の見どころ動画</h3>", ""]

        for cat_key, cat_label in self.CATEGORY_LABELS.items():
            cat_videos = [v for v in videos if v.get("category") == cat_key]

            if cat_videos:
                # Issue #160: 戦術分析はランク優先（is_trusted）、その中で公開日順にソート
                # 安定ソートを利用: まず日付で降順ソート、次に信頼フラグで昇順ソート
                if cat_key == "tactical":
                    cat_videos = sorted(
                        cat_videos,
                        key=lambda v: v.get("published_at", ""),
                        reverse=True,
                    )
                    cat_videos = sorted(
                        cat_videos, key=lambda v: 0 if v.get("is_trusted", False) else 1
                    )

                # メインセクション（表示件数）
                lines.append("<details open>")
                lines.append(
                    f"<summary><strong>{cat_label} ({len(cat_videos)}件)</strong></summary>"
                )
                lines.extend(self.render_video_table(cat_videos))
                lines.append("</details>")
                lines.append("")

        return "\n".join(lines)

    def render_video_table(self, video_list: list) -> list:
        """動画リストをグリッド形式のHTMLに変換（サムネイル付き）"""
        grid_lines = []
        grid_lines.append('<div class="youtube-grid">')

        for v in video_list:
            title = v.get("title", "No Title")
            url = v.get("url", "")
            thumbnail = v.get("thumbnail_url", "")
            channel_display = v.get("channel_display", v.get("channel_name", "Unknown"))
            published_at = v.get("published_at", "")
            query_label = v.get("query_label", "")

            relative_date = DateTimeUtil.format_relative_date(published_at)

            # カード形式で表示
            label_badge = (
                f'<span class="youtube-card-label">{query_label}</span>'
                if query_label
                else ""
            )

            card_html = f"""<div class="youtube-card">
    <a href="{url}" target="_blank" class="youtube-card-thumbnail">
        <img src="{thumbnail}" alt="thumbnail">
    </a>
    <div class="youtube-card-content">
        {label_badge}
        <div class="youtube-card-title">
            <a href="{url}" target="_blank">{title}</a>
        </div>
        <div class="youtube-card-meta">
            <span class="youtube-card-channel">📺 {channel_display}</span>
            <span class="youtube-card-date">🕐 {relative_date}</span>
        </div>
    </div>
</div>"""
            grid_lines.append(card_html)

        grid_lines.append("</div>")
        return grid_lines

    def format_debug_video_section(
        self,
        youtube_videos: dict[str, list[dict]],
        match_key: str,
        match_rank: str = None,
    ) -> str:
        """デバッグ用：対象外動画（ソート落ち、除外）の一覧テーブルを生成 + Importance表示"""
        # Match Keyで該当試合のデータを取得
        video_data = youtube_videos.get(match_key, {})
        if not isinstance(video_data, dict):
            video_data = {}

        # 除外(removed)とソート落ち(overflow)を統合
        removed = video_data.get("removed", [])
        overflow = video_data.get("overflow", [])

        # Issue #133: Importanceがある場合、対象外動画がなくてもセクションを生成
        if not removed and not overflow and not match_rank:
            return ""

        lines = [
            '<details class="collapsible-section">',
            "<summary>🛠️ デバッグ情報</summary>",
            '<div class="section-content">',
        ]

        if match_rank:
            lines.append(f"<p><strong>Importance:</strong> {match_rank}</p>")

        if removed or overflow:
            lines.append("<p><strong>対象外動画一覧</strong></p>")
            lines.append('<div class="debug-video-table-container">')
            lines.append('<table class="debug-video-table">')
            lines.append(
                "<thead><tr><th>Category</th><th>Status</th><th>Title / URL</th><th>Channel</th><th>Date</th><th>Reason</th></tr></thead>"
            )
            lines.append("<tbody>")

            all_excluded = []
            for v in overflow:
                all_excluded.append({**v, "status": "ソート落ち"})
            for v in removed:
                all_excluded.append({**v, "status": "除外"})

            def sort_key(v):
                cat = v.get("category", "")
                keys = list(self.CATEGORY_LABELS.keys())
                try:
                    return keys.index(cat)
                except ValueError:
                    return 999

            all_excluded.sort(key=sort_key)

            for v in all_excluded:
                cat_key = v.get("category", "unknown")
                cat_label = self.CATEGORY_LABELS.get(cat_key, cat_key)
                status = v.get("status", "")
                title = v.get("title", "No Title")
                url = v.get("url", "#")
                channel = v.get("channel_name", "Unknown")
                published = v.get("published_at", "")
                reason = v.get("filter_reason", "-")
                date_display = DateTimeUtil.format_relative_date(published)

                row = f"""<tr>
<td>{cat_label}</td>
<td>{status}</td>
<td><a href="{url}" target="_blank">{title}</a></td>
<td>{channel}</td>
<td>{date_display}</td>
<td>{reason}</td>
</tr>"""
                lines.append(row)

            lines.append("</tbody></table>")
            lines.append("</div>")

        lines.append("</div>")
        lines.append("</details>")

        return "\n".join(lines)
