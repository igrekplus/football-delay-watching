from datetime import datetime
from typing import List, Dict
from src.domain.models import MatchData
import logging
from src.utils.spoiler_filter import SpoilerFilter
from src.utils.formation_image import generate_formation_image
from src.utils.nationality_flags import format_player_with_flag
from config import config

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        pass
    
    def _format_relative_date(self, iso_date: str) -> str:
        """ISO日付を「3日前」のような相対表示に変換"""
        if not iso_date:
            return "不明"
        try:
            import pytz
            # ISO形式をパース（2025-12-19T14:00:00Z）
            pub_date = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            jst = pytz.timezone('Asia/Tokyo')
            now = datetime.now(jst)
            diff = now - pub_date.astimezone(jst)
            
            days = diff.days
            if days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    return "数分前"
                return f"{hours}時間前"
            elif days == 1:
                return "1日前"
            elif days < 7:
                return f"{days}日前"
            elif days < 30:
                weeks = days // 7
                return f"{weeks}週間前"
            elif days < 365:
                months = days // 30
                return f"{months}ヶ月前"
            else:
                return pub_date.strftime("%Y/%m/%d")
        except Exception:
            return iso_date[:10] if len(iso_date) >= 10 else iso_date

    def _format_lineup_by_position(self, lineup: List[str], formation: str, team_name: str, 
                                     nationalities: Dict[str, str] = None, 
                                     player_numbers: Dict[str, int] = None,
                                     player_birthdates: Dict[str, str] = None) -> str:
        """
        フォーメーション情報を元に選手をポジション別に振り分けて表示
        例: 4-3-3 -> GK:1, DF:4, MF:3, FW:3
        国籍情報がある場合は国旗絵文字を追加
        背番号がある場合は先頭に表示
        生年月日がある場合は (YYYY/MM/DD) 形式で表示
        """
        if nationalities is None:
            nationalities = {}
        if player_numbers is None:
            player_numbers = {}
        if player_birthdates is None:
            player_birthdates = {}
            
        def format_birthdate(date_str: str) -> str:
            """YYYY-MM-DD を YYYY/MM/DD に変換"""
            if not date_str:
                return ""
            try:
                return date_str.replace('-', '/')
            except Exception:
                return ""
            
        def format_player(name: str) -> str:
            nationality = nationalities.get(name, "")
            number = player_numbers.get(name)
            birthdate = player_birthdates.get(name, "")
            formatted = format_player_with_flag(name, nationality)
            if number is not None:
                formatted = f"#{number} {formatted}"
            if birthdate:
                formatted = f"{formatted} ({format_birthdate(birthdate)})"
            return formatted
        
        if not lineup or len(lineup) != 11:
            formatted = [format_player(p) for p in lineup] if lineup else []
            return ', '.join(formatted) if formatted else "不明"
        
        # フォーメーションをパース (例: "4-3-3" -> [4, 3, 3])
        try:
            parts = [int(x) for x in formation.split('-')]
        except (ValueError, AttributeError):
            # パース失敗時はカンマ区切りにフォールバック
            formatted = [format_player(p) for p in lineup]
            return ', '.join(formatted)
        
        # GK は常に1人、残りをフォーメーションで振り分け
        gk = format_player(lineup[0])
        outfield = lineup[1:]
        
        positions = []
        idx = 0
        position_names = ['DF', 'MF', 'FW']
        
        for i, count in enumerate(parts):
            if idx + count <= len(outfield):
                players = [format_player(p) for p in outfield[idx:idx + count]]
                pos_name = position_names[i] if i < len(position_names) else 'FW'
                positions.append(f"{pos_name}: {', '.join(players)}")
                idx += count
        
        # 残りの選手がいれば FW に追加
        if idx < len(outfield):
            remaining = [format_player(p) for p in outfield[idx:]]
            positions.append(f"FW: {', '.join(remaining)}")
        
        lines = [f"GK: {gk}"]
        lines.extend(positions)
        return '\n    - '.join(lines)

    def _calculate_age(self, birthdate_str: str) -> int:
        """生年月日から年齢を計算"""
        if not birthdate_str:
            return None
        try:
            from datetime import datetime
            import pytz
            birth = datetime.strptime(birthdate_str, "%Y-%m-%d")
            jst = pytz.timezone('Asia/Tokyo')
            today = datetime.now(jst).replace(tzinfo=None)
            age = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            return age
        except Exception:
            return None

    def _get_player_position(self, index: int, lineup_size: int, formation: str) -> str:
        """選手のインデックスとフォーメーションからポジションを決定"""
        if index == 0:
            return "GK"
        
        # フォーメーションをパース（例: "4-3-3" -> [4, 3, 3]）
        try:
            parts = [int(x) for x in formation.split('-')]
        except (ValueError, AttributeError):
            return "FW"  # パース失敗時
        
        position_names = ['DF', 'MF', 'FW']
        outfield_index = index - 1  # GKを除いたインデックス
        
        cumulative = 0
        for i, count in enumerate(parts):
            cumulative += count
            if outfield_index < cumulative:
                return position_names[i] if i < len(position_names) else 'FW'
        
        return 'FW'

    def _format_player_cards(self, lineup: List[str], formation: str, team_name: str,
                             nationalities: Dict[str, str] = None,
                             player_numbers: Dict[str, int] = None,
                             player_birthdates: Dict[str, str] = None,
                             player_photos: Dict[str, str] = None,
                             position_label: str = None) -> str:
        """
        選手リストをカード形式のHTMLに変換
        
        Args:
            position_label: 全選手に使用するポジションラベル（例: "SUB"）。
                           Noneの場合はフォーメーションから計算
        """
        if nationalities is None:
            nationalities = {}
        if player_numbers is None:
            player_numbers = {}
        if player_birthdates is None:
            player_birthdates = {}
        if player_photos is None:
            player_photos = {}
        
        if not lineup:
            return '<div class="player-cards"><p>選手情報なし</p></div>'
        
        cards_html = []
        for idx, name in enumerate(lineup):
            # ポジションラベルが指定されていればそれを使用、なければフォーメーションから計算
            if position_label:
                position = position_label
            else:
                position = self._get_player_position(idx, len(lineup), formation)
            
            number = player_numbers.get(name)
            nationality = nationalities.get(name, "")
            birthdate = player_birthdates.get(name, "")
            photo_url = player_photos.get(name, "")
            age = self._calculate_age(birthdate)
            
            # 国旗を取得
            flag = format_player_with_flag("", nationality).strip() if nationality else ""
            
            # カードHTML生成
            number_display = f"#{number}" if number is not None else ""
            photo_html = f'<img src="{photo_url}" alt="{name}" class="player-card-photo">' if photo_url else '<div class="player-card-photo player-card-photo-placeholder"></div>'
            age_display = f"{age}歳" if age else ""
            nationality_display = f"{flag} {nationality}" if nationality else ""
            
            card = f'''<div class="player-card">
<div class="player-card-header"><span>{position} {number_display}</span><span>{flag}</span></div>
<div class="player-card-body">
{photo_html}
<div class="player-card-info">
<div class="player-card-name">{name}</div>
<div class="player-card-nationality">{nationality}</div>
<div class="player-card-age">{age_display}</div>
</div>
</div>
</div>'''
            cards_html.append(card)
        
        return f'<div class="player-cards">\n' + '\n'.join(cards_html) + '\n</div>'

    def _format_injury_cards(self, injuries_list: list, player_photos: Dict[str, str] = None) -> str:
        """
        怪我人・出場停止リストをカード形式のHTMLに変換
        """
        if not injuries_list:
            return '<div class="player-cards"><p>なし</p></div>'
        
        if player_photos is None:
            player_photos = {}
        
        cards_html = []
        for injury in injuries_list:
            name = injury.get("name", "Unknown")
            team = injury.get("team", "")
            reason = injury.get("reason", "")
            # injuries_list 内の photo を優先、なければ player_photos から取得
            photo_url = injury.get("photo", "") or player_photos.get(name, "")
            
            photo_html = f'<img src="{photo_url}" alt="{name}" class="player-card-photo">' if photo_url else '<div class="player-card-photo player-card-photo-placeholder"></div>'
            
            card = f'''<div class="player-card injury-card">
<div class="player-card-header"><span>🏥 OUT</span><span></span></div>
<div class="player-card-body">
{photo_html}
<div class="player-card-info">
<div class="player-card-name">{name}</div>
<div class="player-card-nationality">{team}</div>
<div class="player-card-age injury-reason">⚠️ {reason}</div>
</div>
</div>
</div>'''
            cards_html.append(card)
        
        return f'<div class="player-cards">\n' + '\n'.join(cards_html) + '\n</div>'

    def generate(self, matches: List[MatchData], youtube_videos: Dict[str, List[Dict]] = None, youtube_stats: Dict[str, int] = None) -> tuple:
        """
        Generates markdown report string
        
        Returns:
            tuple: (report_content: str, image_paths: List[str])
        """
        if youtube_videos is None:
            youtube_videos = {}
        if youtube_stats is None:
            youtube_stats = {"api_calls": 0, "cache_hits": 0}
            
        lines = []
        image_paths = []  # 生成された画像パスを収集
        
        lines.append(self._write_header(matches))
        report_lines, report_images = self._write_match_reports(matches, youtube_videos)
        lines.append(report_lines)
        image_paths.extend(report_images)
        lines.append(self._write_excluded_list(matches, youtube_stats))
        
        report = "\n".join(lines)
        
        # Determine filename based on current date (run date)
        from datetime import datetime
        import pytz
        import os
        
        jst = pytz.timezone('Asia/Tokyo')
        today_str = datetime.now(jst).strftime('%Y-%m-%d')
        output_dir = config.OUTPUT_DIR # Changed to use config.OUTPUT_DIR
        filename = f"{output_dir}/{today_str}.md" # Corrected filename construction
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
            
        logger.info(f"Report generated: {filename}")
        return report, image_paths

    def _write_header(self, matches: List[MatchData]) -> str:
        target_matches = [m for m in matches if m.is_target]
        lines = [f"# 本日の対象試合（{len(target_matches)}件）\n"]
        for i, match in enumerate(target_matches, 1):
            lines.append(f"{i}. {match.home_team} vs {match.away_team} （{match.competition}／{match.rank}）")
        lines.append("\n")
        return "\n".join(lines)

    def _write_match_reports(self, matches: List[MatchData], youtube_videos: Dict[str, List[Dict]] = None) -> tuple:
        """
        試合レポートを生成
        
        Returns:
            tuple: (report_string: str, image_paths: List[str])
        """
        if youtube_videos is None:
            youtube_videos = {}
            
        lines = []
        image_paths = []
        target_matches = [m for m in matches if m.is_target]
        
        for i, match in enumerate(target_matches, 1):
            lines.append(f"## 試合{i}：{match.home_team} vs {match.away_team} （{match.competition}／{match.rank}）\n")
            
            lines.append("### ■ 基本情報（固定情報）")
            lines.append(f"- 大会：{match.competition}")
            lines.append(f"- 日時：{match.kickoff_jst} / {match.kickoff_local}")
            lines.append(f"- 会場：{match.venue}")
            
            # スタメン選手カード表示（HTML直接出力）
            home_cards_html = self._format_player_cards(
                match.home_lineup, match.home_formation, match.home_team,
                match.player_nationalities, match.player_numbers,
                match.player_birthdates, match.player_photos
            )
            away_cards_html = self._format_player_cards(
                match.away_lineup, match.away_formation, match.away_team,
                match.player_nationalities, match.player_numbers,
                match.player_birthdates, match.player_photos
            )
            lines.append(f"### スタメン（{match.home_team}）フォーメーション: {match.home_formation}")
            lines.append(home_cards_html)
            lines.append(f"### スタメン（{match.away_team}）フォーメーション: {match.away_formation}")
            lines.append(away_cards_html)
            
            # ベンチ選手もカード形式で表示
            home_bench_html = self._format_player_cards(
                match.home_bench, "", match.home_team,
                match.player_nationalities, match.player_numbers,
                match.player_birthdates, match.player_photos,
                position_label="SUB"
            )
            away_bench_html = self._format_player_cards(
                match.away_bench, "", match.away_team,
                match.player_nationalities, match.player_numbers,
                match.player_birthdates, match.player_photos,
                position_label="SUB"
            )
            lines.append(f"### ベンチ（{match.home_team}）")
            lines.append(home_bench_html)
            lines.append(f"### ベンチ（{match.away_team}）")
            lines.append(away_bench_html)
            lines.append(f"- フォーメーション：Home {match.home_formation} / Away {match.away_formation}")
            
            # 怪我人・出場停止情報をカード形式で表示
            lines.append("### 出場停止・負傷者情報")
            injury_cards_html = self._format_injury_cards(match.injuries_list, match.player_photos)
            lines.append(injury_cards_html)
            
            # Format form with icons (W=✅, D=➖, L=❌)
            def format_form_with_icons(form: str) -> str:
                if not form:
                    return ""
                icons = {"W": "✅", "D": "➖", "L": "❌"}
                icon_str = "".join(icons.get(c, c) for c in form)
                return f"{form} ({icon_str})"
            
            home_form = format_form_with_icons(match.home_recent_form)
            away_form = format_form_with_icons(match.away_recent_form)
            lines.append(f"- 直近フォーム：Home {home_form} / Away {away_form}")
            lines.append(f"- 過去の対戦成績：{match.h2h_summary}")
            lines.append(f"- 主審：{match.referee}")
            lines.append("")
            
            # Generate formation diagrams - Firebase Hosting用にpublic/reports/images/に保存
            lines.append("### ■ フォーメーション図")
            web_image_dir = "public/reports"  # Firebase用の出力先
            
            home_img = generate_formation_image(
                match.home_formation, match.home_lineup, match.home_team,
                is_home=True, output_dir=web_image_dir, match_id=match.id,
                player_numbers=match.player_numbers
            )
            away_img = generate_formation_image(
                match.away_formation, match.away_lineup, match.away_team,
                is_home=False, output_dir=web_image_dir, match_id=match.id,
                player_numbers=match.player_numbers
            )
            # Markdown用は相対パス、HTML変換時に/reports/images/xxx.pngに
            if home_img:
                lines.append(f"![{match.home_team}](/reports/{home_img})")
                image_paths.append(f"public/reports/{home_img}")
            if away_img:
                lines.append(f"![{match.away_team}](/reports/{away_img})")
                image_paths.append(f"public/reports/{away_img}")
            lines.append("")
            
            # 選手画像はカードに統合済みのため、このセクションは削除
            
            lines.append("### ■ ニュース要約（600〜1,000字）")
            lines.append(f"- {match.news_summary}")
            lines.append("")
            
            lines.append("### ■ 戦術プレビュー")
            lines.append(f"- {match.tactical_preview}")
            # Issue #30: 有効なURLがある場合のみ出力（プレースホルダは除外）
            if match.preview_url and match.preview_url != "https://example.com/tactical-preview":
                lines.append(f"- URL: {match.preview_url}")
            lines.append("")
            
            lines.append("### ■ 監督・選手コメント")
            lines.append(f"- {match.home_interview}")
            lines.append(f"- {match.away_interview}")
            lines.append("")
            
            # YouTube Videos Section
            match_key = f"{match.home_team} vs {match.away_team}"
            videos = youtube_videos.get(match_key, [])
            if videos:
                lines.append("### ■ 📹 試合前の見どころ動画")
                lines.append("")
                
                # カテゴリ別にグループ化
                category_labels = {
                    "press_conference": "🎤 記者会見",
                    "historic": "⚔️ 因縁",
                    "tactical": "📊 戦術分析",
                    "player_highlight": "⭐ 選手紹介",
                    "training": "🏃 練習風景",
                }
                
                for cat_key, cat_label in category_labels.items():
                    cat_videos = [v for v in videos if v.get("category") == cat_key]
                    if cat_videos:
                        # 折りたたみ開始（details/summary）
                        lines.append(f"<details>")
                        lines.append(f"<summary><strong>{cat_label} ({len(cat_videos)}件)</strong></summary>")
                        
                        # HTMLテーブル形式でサムネイル付き表示
                        lines.append('<table class="youtube-table">')
                        lines.append('<thead><tr><th style="text-align:center">サムネイル</th><th style="text-align:left">動画情報</th></tr></thead>')
                        lines.append('<tbody>')
                        
                        for v in cat_videos:
                            title = v.get('title', 'No Title')
                            if len(title) > 40:
                                title = title[:37] + "..."
                            url = v.get('url', '')
                            thumbnail = v.get('thumbnail_url', '')
                            channel_display = v.get('channel_display', v.get('channel_name', 'Unknown'))
                            published_at = v.get('published_at', '')
                            description = v.get('description', '')[:60].replace('\n', ' ')
                            
                            # 公開日を相対表示に変換
                            relative_date = self._format_relative_date(published_at)
                            
                            # サムネイル画像（小サイズ）+ 情報
                            thumb_cell = f'<a href="{url}" target="_blank"><img src="{thumbnail}" alt="thumb" style="width:120px;height:auto;"></a>' if thumbnail else "-"
                            # チャンネル名を太字、説明文を追加
                            info_html = f'<strong><a href="{url}" target="_blank">{title}</a></strong><br/>'
                            info_html += f'📺 <strong>{channel_display}</strong> ・ 🕐 {relative_date}'
                            if description:
                                info_html += f'<br/><em>{description}...</em>'
                            
                            lines.append(f'<tr><td style="text-align:center">{thumb_cell}</td><td style="text-align:left">{info_html}</td></tr>')
                        
                        lines.append('</tbody>')
                        lines.append('</table>')
                        lines.append("</details>")
                        lines.append("")
                
            
            lines.append("### ■ エラーステータス")
            lines.append(f"- {match.error_status}")
            lines.append("\n")
            
        return "\n".join(lines), image_paths

    def _write_excluded_list(self, matches: List[MatchData], youtube_stats: Dict[str, int] = None) -> str:
        if youtube_stats is None:
            youtube_stats = {"api_calls": 0, "cache_hits": 0}
            
        lines = ["## 選外試合リスト\n"]
        excluded = [m for m in matches if not m.is_target]
        if not excluded:
            lines.append("- なし")
        for match in excluded:
            lines.append(f"- {match.home_team} vs {match.away_team} （{match.competition}）… {match.selection_reason}")
            
        # Append API Quota Info (always show in both debug and production mode)
        lines.append("\n## API使用状況")
        if config.QUOTA_INFO:
            for key, info in config.QUOTA_INFO.items():
                lines.append(f"- {key}: {info}")
        else:
            lines.append("- API-Football: (キャッシュから取得のため情報なし)")
        # Static note for Google APIs
        lines.append("- Google Custom Search API: Check Cloud Console (Quota: 100/day free)")
        
        # YouTube API Stats
        api_calls = youtube_stats.get("api_calls", 0)
        cache_hits = youtube_stats.get("cache_hits", 0)
        total_requests = api_calls + cache_hits
        lines.append(f"- YouTube Data API: {api_calls}回呼び出し (キャッシュ: {cache_hits}件, 合計リクエスト: {total_requests}件)")
        
        # Append execution timestamp
        import pytz
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"\n---\n*レポート生成日時: {now_jst} JST*")
            
        return "\n".join(lines)
