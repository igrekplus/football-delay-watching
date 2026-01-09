from datetime import datetime
from typing import List, Dict, Union
from src.domain.models import MatchData, MatchAggregate
import logging
from src.utils.formation_image import generate_formation_image
from src.utils.nationality_flags import format_player_with_flag
from src.utils.api_stats import ApiStats
from src.utils.datetime_util import DateTimeUtil
from src.formatters import PlayerFormatter, MatchInfoFormatter, YouTubeSectionFormatter, MatchupFormatter
from src.parsers.matchup_parser import parse_matchup_text
from config import config

logger = logging.getLogger(__name__)

class ReportGenerator:
    WEB_IMAGE_DIR = "public/reports"

    def __init__(self):
        self.player_formatter = PlayerFormatter()
        self.match_info_formatter = MatchInfoFormatter()
        self.youtube_formatter = YouTubeSectionFormatter()
        self.matchup_formatter = MatchupFormatter()
    
    def generate_all(self, matches: List[Union[MatchData, MatchAggregate]], youtube_videos: Dict[str, List[Dict]] = None, 
                     youtube_stats: Dict[str, int] = None) -> List[Dict]:
        """
        全試合レポートを生成（新方式: 1試合=1レポート）
        
        Returns:
            List[Dict]: 各試合のレポート情報
            [
                {
                    "match": MatchData,
                    "markdown_content": str,
                    "image_paths": List[str],
                    "filename": str  # "2025-12-27_City_vs_Arsenal_20251228_072100"
                },
                ...
            ]
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
        target_matches = [m for m in matches if m.is_target]
        
        for match in target_matches:
            markdown_content, image_paths = self.generate_single_match(
                match, youtube_videos, excluded_section
            )
            
            filename = match.get_report_filename(generation_datetime)
            
            report_list.append({
                "match": match,
                "markdown_content": markdown_content,
                "image_paths": image_paths,
                "filename": filename
            })
            
            logger.info(f"Generated report for: {match.home_team} vs {match.away_team} -> {filename}")
        
        return report_list
    
    def generate_single_match(self, match: Union[MatchData, MatchAggregate], youtube_videos: Dict[str, List[Dict]], 
                              excluded_section: str) -> tuple:
        """
        1試合分のMarkdownレポートを生成
        
        Returns:
            tuple: (markdown_content: str, image_paths: List[str])
        """
        lines = []
        image_paths = []
        
        # ヘッダー（試合タイトル） - Issue #116: ロゴ付きヘッダー
        # ヘッダー（試合タイトル） - Issue #116 & #130: ロゴ付きヘッダー + 基本情報統合
        # 大会名の表示用変換
        competition_display = "Premier League" if match.competition == "EPL" else match.competition
        
        if match.competition_logo:
            logo_html = f'<img src="{match.competition_logo}" class="competition-logo-header" alt="{match.competition}">'
        else:
            logo_html = ''  # ロゴなしの場合は非表示（スタイルで調整）

        # Issue #133: メタ情報を動的に構築（競技ロゴがある場合は競技名を非表示、Importanceはデバッグ欄へ移動）
        meta_items = []
        if not match.competition_logo:  # ロゴがない場合のみ競技名を表示
            meta_items.append(f'<span class="competition-name">{competition_display}</span>')
        meta_items.append(f'<span class="match-datetime">{match.kickoff_jst} / {match.kickoff_local} @ {match.venue}</span>')
        
        # セパレータで結合
        metadata_html = '<span class="separator">|</span>'.join(meta_items)
        
        header_html = f'''<div class="match-header-container">
    {logo_html}
    <div class="match-header-info">
        <h1>{match.home_team} vs {match.away_team}</h1>
        <div class="match-metadata">
            {metadata_html}
        </div>
    </div>
</div>'''
        lines.append(header_html)
        
        # 試合レポート本文
        match_report, match_images = self._write_single_match_content(match, youtube_videos)
        lines.append(match_report)
        image_paths.extend(match_images)
        
        # 末尾にデバッグ情報とAPI使用状況を追加
        lines.append("\n---\n")
        
        # デバッグ用：対象外動画一覧 + Importance（Issue #133）
        match_key = f"{match.home_team} vs {match.away_team}"
        lines.append(self.youtube_formatter.format_debug_video_section(youtube_videos, match_key, match_rank=match.rank))
        
        lines.append(excluded_section)
        
        return "\n".join(lines), image_paths
    
    def _generate_excluded_section(self, matches: List[Union[MatchData, MatchAggregate]], youtube_stats: Dict[str, int]) -> str:
        """選外試合リストとAPI使用状況のセクションを生成"""
        lines = ["## 選外試合リスト\n"]
        excluded = [m for m in matches if not m.is_target]
        if not excluded:
            lines.append("- なし\n")
        else:
            for match in excluded:
                lines.append(f"- {match.home_team} vs {match.away_team} （{match.competition}）… {match.selection_reason}\n")
        
        lines.append("\n## API使用状況\n")
        
        # ApiStatsから表形式でAPI使用状況を取得
        api_table = ApiStats.format_table()
        lines.append(api_table)
        lines.append("\n")
        lines.append("\n*Gmail API: OAuth認証済みアカウントの送信制限\n")
        
        return "".join(lines)
    
    def _format_form_details_table(self, form_details: list) -> str:
        """直近試合詳細テーブルをHTML形式で生成（Issue #132）"""
        table = '<table class="form-table"><thead><tr><th>日付</th><th>対戦相手</th><th>大会</th><th>スコア</th><th>結果</th></tr></thead><tbody>'
        
        for detail in form_details:
            date_str = detail.get("date", "")
            opponent = detail.get("opponent", "")
            competition = detail.get("competition", "")
            round_info = detail.get("round", "")
            score = detail.get("score", "")
            result = detail.get("result", "")
            
            # Result color class
            result_class = {
                "W": "result-win",
                "D": "result-draw",
                "L": "result-loss"
            }.get(result, "")
            
            # Competition with round (if available)
            comp_display = f"{competition}" if not round_info else f"{competition} ({round_info})"
            
            table += f'<tr><td>{date_str}</td><td>{opponent}</td><td>{comp_display}</td><td>{score}</td><td class="{result_class}">{result}</td></tr>'
        
        table += '</tbody></table>'
        return table
    
    def _write_single_match_content(self, match: Union[MatchData, MatchAggregate], youtube_videos: Dict[str, List[Dict]]) -> tuple:
        """1試合分のレポート本文を生成"""
        lines = []
        image_paths = []
        
        # 基本情報 (ヘッダーに移動したため、ここでの呼び出しはレイアウト調整用などに残すか、完全に削除するか。MatchInfoFormatterは空文字を返すようになった)
        lines.append(self.match_info_formatter.format_match_info_html(match))
        
        # スタメン・ベンチ・負傷者
        home_cards_html = self.player_formatter.format_player_cards(
            match.home_lineup, match.home_formation, match.home_team,
            match.player_nationalities, match.player_numbers,
            match.player_birthdates, match.player_photos,
            player_instagram=match.player_instagram
        )
        away_cards_html = self.player_formatter.format_player_cards(
            match.away_lineup, match.away_formation, match.away_team,
            match.player_nationalities, match.player_numbers,
            match.player_birthdates, match.player_photos,
            player_instagram=match.player_instagram
        )
        home_bench_html = self.player_formatter.format_player_cards(
            match.home_bench, "", match.home_team,
            match.player_nationalities, match.player_numbers,
            match.player_birthdates, match.player_photos,
            position_label="SUB", player_positions=match.player_positions,
            player_instagram=match.player_instagram,
            css_class="player-cards-scroll"
        )
        away_bench_html = self.player_formatter.format_player_cards(
            match.away_bench, "", match.away_team,
            match.player_nationalities, match.player_numbers,
            match.player_birthdates, match.player_photos,
            position_label="SUB", player_positions=match.player_positions,
            player_instagram=match.player_instagram,
            css_class="player-cards-scroll"
        )
        away_bench_html = self.player_formatter.format_player_cards(
            match.away_bench, "", match.away_team,
            match.player_nationalities, match.player_numbers,
            match.player_birthdates, match.player_photos,
            position_label="SUB", player_positions=match.player_positions,
            player_instagram=match.player_instagram,
            css_class="player-cards-scroll"
        )
        
        home_logo_html = f'<img src="{match.home_logo}" alt="{match.home_team}" class="team-logo">' if match.home_logo else ''
        away_logo_html = f'<img src="{match.away_logo}" alt="{match.away_team}" class="team-logo">' if match.away_logo else ''
        
        home_injuries = [i for i in match.injuries_list if i.get("team", "") == match.home_team]
        away_injuries = [i for i in match.injuries_list if i.get("team", "") == match.away_team]
        home_injury_html = self.player_formatter.format_injury_cards(home_injuries, match.player_photos, css_class="player-cards-scroll")
        away_injury_html = self.player_formatter.format_injury_cards(away_injuries, match.player_photos, css_class="player-cards-scroll")
        
        # チームセクション（2カラムレイアウト）
        lines.append('<div class="two-column-section">')
        
        # ホームチーム
        lines.append('<div class="team-column">')
        lines.append(f'<h3 class="lineup-header">{home_logo_html} {match.home_team}（{match.home_formation}）</h3>')
        lines.append('<div class="section-label">Starting XI</div>')
        lines.append(home_cards_html)
        lines.append('<div class="section-label">Substitutes</div>')
        lines.append(home_bench_html)
        lines.append('<div class="section-label">Injuries / Suspended</div>')
        lines.append(home_injury_html)
        lines.append('</div>')
        
        # アウェイチーム
        lines.append('<div class="team-column">')
        lines.append(f'<h3 class="lineup-header">{away_logo_html} {match.away_team}（{match.away_formation}）</h3>')
        lines.append('<div class="section-label">Starting XI</div>')
        lines.append(away_cards_html)
        lines.append('<div class="section-label">Substitutes</div>')
        lines.append(away_bench_html)
        lines.append('<div class="section-label">Injuries / Suspended</div>')
        lines.append(away_injury_html)
        lines.append('</div>')
        
        # アウェイチーム (Duplicate removal needed in manual check but strictly replacing block here)
        
        lines.append('</div>')  # end two-column-section
        
        lines.append(f"- 主審：{match.referee}")
        lines.append("")
        
        # Recent Form Details Section (Issue #132)
        lines.append("### ■ 直近5試合")
        
        if match.home_recent_form_details or match.away_recent_form_details:
            lines.append('<div class="two-column-section">')
            
            # Home Team Form Table
            lines.append('<div class="form-column">')
            lines.append(f'<h4>{match.home_team}</h4>')
            if match.home_recent_form_details:
                lines.append(self._format_form_details_table(match.home_recent_form_details))
            else:
                lines.append('<p class="form-empty">データなし</p>')
            lines.append('</div>')
            
            # Away Team Form Table
            lines.append('<div class="form-column">')
            lines.append(f'<h4>{match.away_team}</h4>')
            if match.away_recent_form_details:
                lines.append(self._format_form_details_table(match.away_recent_form_details))
            else:
                lines.append('<p class="form-empty">データなし</p>')
            lines.append('</div>')
            
            lines.append('</div>')  # end two-column-section
        else:
            lines.append('<p class="form-empty">直近試合データなし</p>')
        lines.append("")
        
        # H2H Section (Issue #105)
        lines.append("### ■ 過去の対戦成績")
        lines.append(f"<p class=\"h2h-summary\">{match.h2h_summary}</p>")
        
        if match.h2h_details:
            h2h_table = '<table class="h2h-table"><thead><tr><th>日付</th><th>大会</th><th>対戦</th><th>スコア</th></tr></thead><tbody>'
            for detail in match.h2h_details:
                date_str = detail.get("date", "")
                competition = detail.get("competition", "")
                home_name = detail.get("home", "")
                away_name = detail.get("away", "")
                score = detail.get("score", "")
                winner = detail.get("winner", "")
                
                # Highlight winner
                if winner == home_name:
                    home_display = f"<strong>{home_name}</strong>"
                    away_display = away_name
                elif winner == away_name:
                    home_display = home_name
                    away_display = f"<strong>{away_name}</strong>"
                else:
                    home_display = home_name
                    away_display = away_name
                
                h2h_table += f'<tr><td>{date_str}</td><td>{competition}</td><td>{home_display} vs {away_display}</td><td>{score}</td></tr>'
            h2h_table += '</tbody></table>'
            lines.append(h2h_table)
        lines.append("")
        
        # フォーメーション図
        lines.append("### ■ フォーメーション図")
        
        home_img = generate_formation_image(
            match.home_formation, match.home_lineup, match.home_team,
            is_home=True, output_dir=self.WEB_IMAGE_DIR, match_id=match.id,
            player_numbers=match.player_numbers
        )
        away_img = generate_formation_image(
            match.away_formation, match.away_lineup, match.away_team,
            is_home=False, output_dir=self.WEB_IMAGE_DIR, match_id=match.id,
            player_numbers=match.player_numbers
        )
        
        # Wrap images in container for side-by-side display
        formation_html = '<div class="formation-container">'
        if home_img:
            formation_html += f'<img src="{home_img}" alt="{match.home_team}">'
            image_paths.append(f"{self.WEB_IMAGE_DIR}/{home_img}")
        if away_img:
            formation_html += f'<img src="{away_img}" alt="{match.away_team}">'
            image_paths.append(f"{self.WEB_IMAGE_DIR}/{away_img}")
        formation_html += '</div>'
        lines.append(formation_html)
        lines.append("")
        
        # 同国対決（Issue #39, #141）
        if match.same_country_text:
            matchups = parse_matchup_text(match.same_country_text)
            if matchups:
                team_logos = {
                    match.home_team: match.home_logo,
                    match.away_team: match.away_logo,
                }
                matchup_html = self.matchup_formatter.format_matchup_section(
                    matchups=matchups,
                    player_photos=match.player_photos,
                    team_logos=team_logos,
                    section_title="■ 同国対決"
                )
                lines.append(matchup_html)
            else:
                # パース失敗時は従来のテキスト表示にフォールバック
                lines.append("### ■ 同国対決")
                lines.append(f"\n{match.same_country_text}\n")
            lines.append("")
        
        # 古巣対決（Issue #20）
        if match.former_club_trivia:
            lines.append("### ■ 古巣対決")
            lines.append(f"\n{match.former_club_trivia}\n")
            lines.append("")
        
        # ニュース・戦術 (collapsible on mobile) - Issue #130: Enable Markdown inside details
        # Pre-convert Markdown to HTML since md_in_html extension has issues with our structure
        import markdown as md_lib
        
        news_html = md_lib.markdown(match.news_summary, extensions=['nl2br'])
        # tactical_html = md_lib.markdown(match.tactical_preview, extensions=['nl2br'])
        tactical_html = self._format_tactical_preview_with_visuals(match, md_lib)
        if match.preview_url and match.preview_url != "https://example.com/tactical-preview":
            tactical_html += f'\n<p><a href="{match.preview_url}">戦術プレビュー詳細</a></p>'
        
        lines.append('<details class="collapsible-section" open>')
        lines.append('<summary>📰 ニュース要約</summary>')
        lines.append('<div class="section-content">')
        lines.append(news_html)
        lines.append('</div>')
        lines.append('</details>')
        lines.append("")
        
        lines.append('<details class="collapsible-section" open>')
        lines.append('<summary>📊 戦術プレビュー</summary>')
        lines.append('<div class="section-content">')
        lines.append(tactical_html)
        lines.append('</div>')
        lines.append('</details>')
        lines.append("")
        
        # 監督セクション (collapsible on mobile) - Issue #130: New Layout
        # Pre-convert manager interview Markdown to HTML
        home_interview_html = md_lib.markdown(match.home_interview, extensions=['nl2br']) if match.home_interview else ''
        away_interview_html = md_lib.markdown(match.away_interview, extensions=['nl2br']) if match.away_interview else ''
        lines.append('<details class="collapsible-section" open>')
        lines.append('<summary>🎙️ 監督プレビュー</summary>')
        lines.append('<div class="section-content">')
        home_manager_photo_html = f'<img src="{match.home_manager_photo}" alt="{match.home_manager}" class="manager-photo">' if match.home_manager_photo else '<div class="manager-photo manager-photo-placeholder">👤</div>'
        away_manager_photo_html = f'<img src="{match.away_manager_photo}" alt="{match.away_manager}" class="manager-photo">' if match.away_manager_photo else '<div class="manager-photo manager-photo-placeholder">👤</div>'
        # ロゴ
        home_team_logo = f'<img src="{match.home_logo}" alt="{match.home_team}" class="manager-team-logo">' if match.home_logo else ''
        away_team_logo = f'<img src="{match.away_logo}" alt="{match.away_team}" class="manager-team-logo">' if match.away_logo else ''
        
        manager_section_html = f'''<div class="manager-section">
<div class="manager-card">
    <div class="manager-identity">
        {home_team_logo}
        {home_manager_photo_html}
        <div class="manager-text-info">
            <div class="manager-team">{match.home_team}</div>
            <div class="manager-name">{match.home_manager}</div>
        </div>
    </div>
    <div class="manager-comment">{home_interview_html}</div>
</div>
<div class="manager-card">
    <div class="manager-identity">
        {away_team_logo}
        {away_manager_photo_html}
        <div class="manager-text-info">
            <div class="manager-team">{match.away_team}</div>
            <div class="manager-name">{match.away_manager}</div>
        </div>
    </div>
    <div class="manager-comment">{away_interview_html}</div>
</div>
</div>'''
        lines.append(manager_section_html)

        lines.append('</div>')
        lines.append('</details>')
        lines.append("")
        
        # YouTube動画
        match_key = f"{match.home_team} vs {match.away_team}"
        video_data = youtube_videos.get(match_key, {})
        lines.append(self.youtube_formatter.format_youtube_section(video_data, match_key))
        
        return "\n".join(lines), image_paths

    def _format_tactical_preview_with_visuals(self, match, md_lib) -> str:
        """戦術プレビュー内のキーマッチアップをビジュアル化"""
        text = match.tactical_preview
        if not text:
            return ""
            
        # キーマッチアップセクションを検索
        separator = "### 🔥 キーマッチアップ"
        parts = text.split(separator)
        
        if len(parts) < 2:
            return md_lib.markdown(text, extensions=['nl2br'])
            
        pre_text = parts[0]
        matchup_text = parts[1]
        rest_text = ""
        
        # 後続セクションがある場合（念のため）
        import re
        next_section_match = re.search(r'\n### ', matchup_text)
        if next_section_match:
             rest_text = matchup_text[next_section_match.start():]
             matchup_text = matchup_text[:next_section_match.start()]
             
        # マッチアップをパース
        matchups = parse_matchup_text(matchup_text)
        
        if not matchups:
            return md_lib.markdown(text, extensions=['nl2br'])
            
        # ビジュアルカードの生成
        team_logos = {
            match.home_team: match.home_logo,
            match.away_team: match.away_logo,
        }
        
        matchup_html = self.matchup_formatter.format_matchup_section(
            matchups=matchups,
            player_photos=match.player_photos,
            team_logos=team_logos,
            section_title="🔥 キーマッチアップ"
        )
        
        # HTMLの結合
        html = md_lib.markdown(pre_text, extensions=['nl2br'])
        html += matchup_html
        if rest_text:
            html += md_lib.markdown(rest_text, extensions=['nl2br'])
            
        return html

