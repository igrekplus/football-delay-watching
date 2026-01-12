from datetime import datetime
from typing import List, Dict
from src.domain.models import MatchAggregate
import logging
from src.utils.formation_image import get_formation_layout_data
from src.utils.nationality_flags import format_player_with_flag
from src.utils.api_stats import ApiStats
from src.utils.datetime_util import DateTimeUtil
from src.formatters import PlayerFormatter, MatchInfoFormatter, YouTubeSectionFormatter, MatchupFormatter
from src.parsers import parse_matchup_text, parse_key_player_text
from config import config
import re

logger = logging.getLogger(__name__)

class ReportGenerator:
    WEB_IMAGE_DIR = "public/reports"

    def __init__(self):
        self.player_formatter = PlayerFormatter()
        self.match_info_formatter = MatchInfoFormatter()
        self.youtube_formatter = YouTubeSectionFormatter()
        self.matchup_formatter = MatchupFormatter()
    
    def generate_all(self, matches: List[MatchAggregate], youtube_videos: Dict[str, List[Dict]] = None, 
                     youtube_stats: Dict[str, int] = None) -> List[Dict]:
        """
        全試合レポートを生成（新方式: 1試合=1レポート）
        """
        if youtube_videos is None:
            youtube_videos = {}
        if youtube_stats is None:
            youtube_stats = {"api_calls": 0, "cache_hits": 0}
        
        # 共通セクションを生成
        excluded_section = self._generate_excluded_section(matches, youtube_stats)
        
        # 各試合のレポートを生成
        generation_datetime = DateTimeUtil.format_filename_datetime()
        
        report_list = []
        target_matches = [m for m in matches if m.core.is_target]
        
        for match in target_matches:
            markdown_content, image_paths = self.generate_single_match(
                match, youtube_videos, excluded_section
            )
            
            # MatchCore に get_report_filename があるか、MatchAggregate にあるか
            # model.py を見ると MatchAggregate に実装されているのでそのまま
            filename = match.get_report_filename(generation_datetime)
            
            report_list.append({
                "match": match,
                "markdown_content": markdown_content,
                "image_paths": image_paths,
                "filename": filename
            })
            
            logger.info(f"Generated report for: {match.core.home_team} vs {match.core.away_team} -> {filename}")
        
        return report_list
    
    def generate_single_match(self, match: MatchAggregate, youtube_videos: Dict[str, List[Dict]], 
                               excluded_section: str) -> tuple:
        """
        1試合分のHTMLレポートを生成（選手名カタカナ変換込み）
        """
        from src.template_engine import render_template
        from config import config
        from src.utils.name_translator import NameTranslator
        
        # デバッグ/モックモードの見出し設定
        mode_prefix = ""
        mode_banner = ""
        if config.USE_MOCK_DATA:
            mode_prefix = "[MOCK] "
            mode_banner = '<div class="mode-banner mode-banner-mock">🧪 MOCK MODE - このレポートはモックデータです</div>'
        elif config.DEBUG_MODE:
            mode_prefix = "[DEBUG] "
            mode_banner = '<div class="mode-banner mode-banner-debug">🔧 DEBUG MODE - このレポートはデバッグ用です</div>'

        # 生成日時
        from src.utils.datetime_util import DateTimeUtil
        timestamp = DateTimeUtil.format_display_timestamp()
        
        # コンテキストデータの準備
        image_paths = []
        match_report_context, match_images = self._get_match_report_context(match, youtube_videos)
        image_paths.extend(match_images)
        
        # 追加情報の統合
        match_report_context.update({
            "mode_prefix": mode_prefix,
            "mode_banner": mode_banner,
            "timestamp": timestamp,
            "excluded_section": excluded_section,
            "competition_display": "Premier League" if match.core.competition == "EPL" else match.core.competition
        })
        
        # テンプレートでレンダリング
        html_content = render_template("report.html", **match_report_context)
        
        # 選手名をカタカナに変換（全体）
        player_names = self._extract_player_names(match)
        translator = NameTranslator()
        if player_names:
            html_content = translator.translate_names_in_html(html_content, player_names)
        
        return html_content, image_paths
    
    def _generate_excluded_section(self, matches: List[MatchAggregate], youtube_stats: Dict[str, int]) -> str:
        """選外試合リストとAPI使用状況のセクションを生成（HTML形式）"""
        excluded = [m for m in matches if not m.core.is_target]
        
        html_parts = ['<div class="debug-info">']
        html_parts.append('<h3>選外試合リスト</h3>')
        if not excluded:
            html_parts.append('<p>なし</p>')
        else:
            html_parts.append('<ul>')
            for match in excluded:
                html_parts.append(f'<li>{match.core.home_team} vs {match.core.away_team} （{match.core.competition}）… {match.core.selection_reason}</li>')
            html_parts.append('</ul>')
        
        html_parts.append('<h3>API使用状況</h3>')
        api_table = ApiStats.format_table()  # Markdown table
        # Convert Markdown table to HTML
        html_parts.append(self._markdown_table_to_html(api_table))
        html_parts.append('<p><small>*Gmail API: OAuth認証済みアカウントの送信制限</small></p>')
        html_parts.append('</div>')
        
        return "\n".join(html_parts)
    
    def _markdown_table_to_html(self, md_table: str) -> str:
        """Markdown テーブルを HTML テーブルに変換"""
        lines = [line.strip() for line in md_table.strip().split('\n') if line.strip()]
        if not lines:
            return ""
        
        html = ['<table class="api-stats-table">']
        for i, line in enumerate(lines):
            if line.startswith('|---') or line.startswith('| ---'):
                continue  # Skip separator line
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            tag = 'th' if i == 0 else 'td'
            row_tag = 'thead' if i == 0 else 'tbody'
            if i == 0:
                html.append(f'<{row_tag}><tr>')
            elif i == 1 or (i > 1 and '</tbody>' not in html[-1]):
                if i == 1:
                    html.append('<tbody>')
                html.append('<tr>')
            for cell in cells:
                # Convert Markdown links to HTML
                cell = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', cell)
                html.append(f'<{tag}>{cell}</{tag}>')
            html.append('</tr>')
            if i == 0:
                html.append(f'</{row_tag}>')
        html.append('</tbody>')
        html.append('</table>')
        return '\n'.join(html)

    
    def _format_form_details_table(self, form_details: list) -> str:
        """直近試合詳細テーブルをHTML形式で生成"""
        from src.template_engine import render_template
        return render_template("partials/form_table.html", form_details=form_details)
    
    def _get_match_report_context(self, match: MatchAggregate, youtube_videos: Dict[str, List[Dict]]) -> tuple:
        """
        1試合分のレポート用コンテキストデータを生成
        
        Returns:
            (context_dict, image_paths)
        """
        from src.template_engine import render_template
        from src.utils.name_translator import NameTranslator
        import markdown as md_lib
        
        image_paths = []
        
        # デバッグ/モックモードの見出し設定
        mode_prefix = ""
        mode_banner = ""
        if config.USE_MOCK_DATA:
            mode_prefix = "[MOCK] "
            mode_banner = '<div class="mode-banner mode-banner-mock">🧪 MOCK MODE - このレポートはモックデータです</div>'
        elif config.DEBUG_MODE:
            mode_prefix = "[DEBUG] "
            mode_banner = '<div class="mode-banner mode-banner-debug">🔧 DEBUG MODE - このレポートはデバッグ用です</div>'

        # 生成日時
        from src.utils.datetime_util import DateTimeUtil
        timestamp = DateTimeUtil.format_display_timestamp()
        
        # コンテキストデータの準備
        image_paths = []
        
        # 選手名をカタカナに変換（フォーメーション図の短縮名用にも必要）
        from src.utils.name_translator import NameTranslator
        player_names = self._extract_player_names(match)
        translator = NameTranslator()
        # フォーメーション図用の短縮名辞書を取得
        short_names_dict = translator.get_short_names(player_names)

        print(f"DEBUG: Home Logo: {match.core.home_logo}, Away Logo: {match.core.away_logo}")

        # 選手カードの生成（Jinja2版 format_player_cards は既に内部で render_template している）
        home_cards_html = self.player_formatter.format_player_cards(
            match.facts.home_lineup, match.facts.home_formation, match.core.home_team,
            match.facts.player_nationalities, match.facts.player_numbers,
            match.facts.player_birthdates, match.facts.player_photos,
            player_instagram=match.facts.player_instagram
        )
        away_cards_html = self.player_formatter.format_player_cards(
            match.facts.away_lineup, match.facts.away_formation, match.core.away_team,
            match.facts.player_nationalities, match.facts.player_numbers,
            match.facts.player_birthdates, match.facts.player_photos,
            player_instagram=match.facts.player_instagram
        )
        home_bench_html = self.player_formatter.format_player_cards(
            match.facts.home_bench, "", match.core.home_team,
            match.facts.player_nationalities, match.facts.player_numbers,
            match.facts.player_birthdates, match.facts.player_photos,
            position_label="SUB", player_positions=match.facts.player_positions,
            player_instagram=match.facts.player_instagram,
            css_class="player-cards-scroll"
        )
        away_bench_html = self.player_formatter.format_player_cards(
            match.facts.away_bench, "", match.core.away_team,
            match.facts.player_nationalities, match.facts.player_numbers,
            match.facts.player_birthdates, match.facts.player_photos,
            position_label="SUB", player_positions=match.facts.player_positions,
            player_instagram=match.facts.player_instagram,
            css_class="player-cards-scroll"
        )
        
        home_injuries = [i for i in match.facts.injuries_list if i.get("team", "") == match.core.home_team]
        away_injuries = [i for i in match.facts.injuries_list if i.get("team", "") == match.core.away_team]
        home_injury_html = self.player_formatter.format_injury_cards(home_injuries, match.facts.player_photos, css_class="player-cards-scroll")
        away_injury_html = self.player_formatter.format_injury_cards(away_injuries, match.facts.player_photos, css_class="player-cards-scroll")
        
        # フォーメーションデータ
        home_formation_data = get_formation_layout_data(
            formation=match.facts.home_formation,
            players=match.facts.home_lineup,
            team_name=match.core.home_team,
            team_logo=match.core.home_logo,
            team_color=match.facts.home_team_color,
            is_home=True,
            player_nationalities=match.facts.player_nationalities,
            player_numbers=match.facts.player_numbers,
            player_photos=match.facts.player_photos,
            player_short_names=short_names_dict
        )
        away_formation_data = get_formation_layout_data(
            formation=match.facts.away_formation,
            players=match.facts.away_lineup,
            team_name=match.core.away_team,
            team_logo=match.core.away_logo,
            team_color=match.facts.away_team_color,
            is_home=False,
            player_nationalities=match.facts.player_nationalities,
            player_numbers=match.facts.player_numbers,
            player_photos=match.facts.player_photos,
            player_short_names=short_names_dict
        )

        formation_html = render_template("partials/formation_section.html",
                                          home=home_formation_data, 
                                          away=away_formation_data)
        
        # 同国対決
        same_country_html = ""
        if match.facts.same_country_text:
            matchups = parse_matchup_text(match.facts.same_country_text)
            if matchups:
                team_logos = {
                    match.core.home_team: match.core.home_logo,
                    match.core.away_team: match.core.away_logo,
                }
                same_country_html = self.matchup_formatter.format_matchup_section(
                    matchups=matchups,
                    player_photos=match.facts.player_photos,
                    team_logos=team_logos,
                    section_title="■ 同国対決"
                )
            else:
                same_country_html = f"<h3>■ 同国対決</h3><p>{match.facts.same_country_text}</p>"

        # ニュース・戦術プレビュー・古巣対決
        news_html = md_lib.markdown(match.preview.news_summary, extensions=['nl2br'])
        tactical_html = self._format_tactical_preview_with_visuals(match, md_lib)
        
        # 古巣対決（Markdownを変換）
        former_club_html = ""
        if match.facts.former_club_trivia:
            former_club_html = md_lib.markdown(match.facts.former_club_trivia, extensions=['nl2br'])
        
        # 監督コメント
        home_interview_html = md_lib.markdown(match.preview.home_interview, extensions=['nl2br']) if match.preview.home_interview else ''
        away_interview_html = md_lib.markdown(match.preview.away_interview, extensions=['nl2br']) if match.preview.away_interview else ''
        manager_section_html = render_template("partials/manager_section.html",
                                               home_team_logo=match.core.home_logo,
                                               home_manager_photo=match.facts.home_manager_photo,
                                               home_team=match.core.home_team,
                                               home_manager=match.facts.home_manager,
                                               home_interview=home_interview_html,
                                               away_team_logo=match.core.away_logo,
                                               away_manager_photo=match.facts.away_manager_photo,
                                               away_team=match.core.away_team,
                                               away_manager=match.facts.away_manager,
                                               away_interview=away_interview_html)

        # 移籍情報
        home_transfer_html = md_lib.markdown(match.preview.home_transfer_news, extensions=['nl2br']) if match.preview.home_transfer_news else ''
        away_transfer_html = md_lib.markdown(match.preview.away_transfer_news, extensions=['nl2br']) if match.preview.away_transfer_news else ''
        transfer_section_html = render_template("partials/transfer_section.html",
                                                home_team_logo=match.core.home_logo,
                                                home_team=match.core.home_team,
                                                home_transfer_html=home_transfer_html,
                                                away_team_logo=match.core.away_logo,
                                                away_team=match.core.away_team,
                                                away_transfer_html=away_transfer_html)

        # YouTube
        match_key = f"{match.core.home_team} vs {match.core.away_team}"
        video_data = youtube_videos.get(match_key, {})
        youtube_html = self.youtube_formatter.format_youtube_section(video_data, match_key)
        debug_youtube_html = self.youtube_formatter.format_debug_video_section(youtube_videos, match_key, match_rank=match.core.rank)
        
        context = {
            "match": match,
            "match_info_html": self.match_info_formatter.format_match_info_html(match),
            "home_cards_html": home_cards_html,
            "away_cards_html": away_cards_html,
            "home_bench_html": home_bench_html,
            "away_bench_html": away_bench_html,
            "home_injury_html": home_injury_html,
            "away_injury_html": away_injury_html,
            "formation_html": formation_html,
            "has_recent_form": bool(match.facts.home_recent_form_details or match.facts.away_recent_form_details),
            "same_country_html": same_country_html,
            "news_html": news_html,
            "tactical_html": tactical_html,
            "manager_section_html": manager_section_html,
            "transfer_section_html": transfer_section_html,
            "former_club_html": former_club_html,
            "youtube_html": youtube_html,
            "debug_youtube_html": debug_youtube_html
        }
        
        return context, image_paths

    def _format_tactical_preview_with_visuals(self, match, md_lib) -> str:
        """戦術プレビュー内の各セクションを個別にビジュアル化して結合"""
        import re
        from src.parsers.tactical_style_parser import parse_tactical_style_text
        
        text = match.preview.tactical_preview
        if not text:
            return ""

        team_logos = {
            match.core.home_team: match.core.home_logo,
            match.core.away_team: match.core.away_logo,
        }

        # セクション見出しで分割
        # 戻り値は [リード文, 見出し1, 内容1, 見出し2, 内容2, ...] の形式
        parts = re.split(r'\n(### .+)', "\n" + text)
        
        lead_text = parts[0].strip()
        final_html = ""
        
        if lead_text:
            final_html += md_lib.markdown(lead_text, extensions=['nl2br'])

        # セクションごとに処理
        for i in range(1, len(parts), 2):
            # 見出しから "### " と余分な空白を削除
            title_raw = parts[i].strip()
            title = re.sub(r'^###\s*', '', title_raw)
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            
            if "⚽ キープレイヤー" in title:
                key_players = parse_key_player_text(content)
                if key_players:
                    final_html += self.matchup_formatter.format_key_player_section(
                        key_players=key_players,
                        player_photos=match.facts.player_photos,
                        team_logos=team_logos,
                        section_title=title
                    )
                else:
                    final_html += md_lib.markdown(f"### {title}\n{content}", extensions=['nl2br'])
            
            elif "🎯 戦術スタイル" in title:
                tactical_styles = parse_tactical_style_text(content, match.core.home_team, match.core.away_team)
                if tactical_styles:
                    final_html += self.matchup_formatter.format_tactical_style_section(
                        tactical_styles=tactical_styles,
                        team_logos=team_logos,
                        section_title=title
                    )
                else:
                    final_html += md_lib.markdown(f"### {title}\n{content}", extensions=['nl2br'])
                    
            elif "🔥 キーマッチアップ" in title:
                matchups = parse_matchup_text(content)
                if matchups:
                    final_html += self.matchup_formatter.format_matchup_section(
                        matchups=matchups,
                        player_photos=match.facts.player_photos,
                        team_logos=team_logos,
                        section_title=title
                    )
                else:
                    final_html += md_lib.markdown(f"### {title}\n{content}", extensions=['nl2br'])
            
            else:
                # 未知のセクションはそのままMarkdownとして処理
                final_html += md_lib.markdown(f"### {title}\n{content}", extensions=['nl2br'])

        return final_html


    def _extract_player_names(self, match: MatchAggregate) -> List[str]:
        """
        Extract player names from match data
        
        Returns:
            List of player names
        """
        names = []
        
        # スタメン
        if match.facts.home_lineup:
            names.extend(match.facts.home_lineup)
        if match.facts.away_lineup:
            names.extend(match.facts.away_lineup)
        
        # ベンチ
        if match.facts.home_bench:
            names.extend(match.facts.home_bench)
        if match.facts.away_bench:
            names.extend(match.facts.away_bench)
        
        # 負傷者
        if match.facts.injuries_list:
            for injury in match.facts.injuries_list:
                if injury.get("player"):
                    names.append(injury["player"])
        
        # 監督名
        if match.facts.home_manager:
            names.append(match.facts.home_manager)
        if match.facts.away_manager:
            names.append(match.facts.away_manager)
        
        # 同国対決セクションから抽出
        if match.facts.same_country_text:
            matchups = parse_matchup_text(match.facts.same_country_text)
            for m in matchups:
                names.extend([m.player1_name, m.player2_name])
        
        # 戦術プレビューのキープレイヤーから抽出
        if match.preview.tactical_preview:
            kp_separator = "### ⚽ キープレイヤー"
            parts = match.preview.tactical_preview.split(kp_separator)
            if len(parts) >= 2:
                kp_content = parts[1]
                next_section_match = re.search(r'\n### ', kp_content)
                if next_section_match:
                    kp_content = kp_content[:next_section_match.start()]
                
                key_players = parse_key_player_text(kp_content)
                for p in key_players:
                    names.append(p.name)

        # 戦術プレビューのキーマッチアップから抽出
        if match.preview.tactical_preview:
             # キーマッチアップ部分を抽出（_format_tactical_preview_with_visuals と同じロジック）
            separator = "### 🔥 キーマッチアップ"
            parts = match.preview.tactical_preview.split(separator)
            if len(parts) >= 2:
                matchup_text = parts[1]
                next_section_match = re.search(r'\n### ', matchup_text)
                if next_section_match:
                    matchup_text = matchup_text[:next_section_match.start()]
                
                matchups = parse_matchup_text(matchup_text)
                for m in matchups:
                    names.extend([m.player1_name, m.player2_name])
        
        return names
