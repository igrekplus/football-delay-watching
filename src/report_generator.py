from datetime import datetime
from typing import List, Dict
from src.domain.models import MatchAggregate
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
        1試合分のMarkdownレポートを生成
        """
        from src.template_engine import render_template
        from config import config
        
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
        markdown_content = render_template("report.html", **match_report_context)
        
        return markdown_content, image_paths
    
    def _generate_excluded_section(self, matches: List[MatchAggregate], youtube_stats: Dict[str, int]) -> str:
        """選外試合リストとAPI使用状況のセクションを生成"""
        lines = ["## 選外試合リスト\n"]
        excluded = [m for m in matches if not m.core.is_target]
        if not excluded:
            lines.append("- なし\n")
        else:
            for match in excluded:
                lines.append(f"- {match.core.home_team} vs {match.core.away_team} （{match.core.competition}）… {match.core.selection_reason}\n")
        
        lines.append("\n## API使用状況\n")
        api_table = ApiStats.format_table()
        lines.append(api_table)
        lines.append("\n")
        lines.append("\n*Gmail API: OAuth認証済みアカウントの送信制限\n")
        
        return "".join(lines)
    
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
        import markdown as md_lib
        
        image_paths = []
        
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
        
        # フォーメーション図
        home_img = generate_formation_image(
            match.facts.home_formation, match.facts.home_lineup, match.core.home_team,
            is_home=True, output_dir=self.WEB_IMAGE_DIR, match_id=match.core.id,
            player_numbers=match.facts.player_numbers
        )
        away_img = generate_formation_image(
            match.facts.away_formation, match.facts.away_lineup, match.core.away_team,
            is_home=False, output_dir=self.WEB_IMAGE_DIR, match_id=match.core.id,
            player_numbers=match.facts.player_numbers
        )
        
        formation_html = render_template("partials/formation_section.html",
                                          home_img=home_img, away_img=away_img,
                                          home_team=match.core.home_team, away_team=match.core.away_team)
        if home_img: image_paths.append(f"{self.WEB_IMAGE_DIR}/{home_img}")
        if away_img: image_paths.append(f"{self.WEB_IMAGE_DIR}/{away_img}")
        
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
                same_country_html = f"### ■ 同国対決\n\n{match.facts.same_country_text}\n"

        # ニュース・戦術プレビュー
        news_html = md_lib.markdown(match.preview.news_summary, extensions=['nl2br'])
        tactical_html = self._format_tactical_preview_with_visuals(match, md_lib)
        
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
            "youtube_html": youtube_html,
            "debug_youtube_html": debug_youtube_html
        }
        
        return context, image_paths

    def _format_tactical_preview_with_visuals(self, match, md_lib) -> str:
        """戦術プレビュー内のキーマッチアップをビジュアル化"""
        text = match.preview.tactical_preview
        if not text:
            return ""
            
        separator = "### 🔥 キーマッチアップ"
        parts = text.split(separator)
        
        if len(parts) < 2:
            return md_lib.markdown(text, extensions=['nl2br'])
            
        pre_text = parts[0]
        matchup_text = parts[1]
        rest_text = ""
        
        import re
        next_section_match = re.search(r'\n### ', matchup_text)
        if next_section_match:
             rest_text = matchup_text[next_section_match.start():]
             matchup_text = matchup_text[:next_section_match.start()]
             
        matchups = parse_matchup_text(matchup_text)
        
        if not matchups:
            return md_lib.markdown(text, extensions=['nl2br'])
            
        team_logos = {
            match.core.home_team: match.core.home_logo,
            match.core.away_team: match.core.away_logo,
        }
        
        matchup_html = self.matchup_formatter.format_matchup_section(
            matchups=matchups,
            player_photos=match.facts.player_photos,
            team_logos=team_logos,
            section_title="🔥 キーマッチアップ"
        )
        
        html = md_lib.markdown(pre_text, extensions=['nl2br'])
        html += matchup_html
        if rest_text:
            html += md_lib.markdown(rest_text, extensions=['nl2br'])
            
        return html

