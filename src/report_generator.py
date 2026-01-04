from datetime import datetime
from typing import List, Dict, Union
from src.domain.models import MatchData, MatchAggregate
import logging
from src.utils.formation_image import generate_formation_image
from src.utils.nationality_flags import format_player_with_flag
from src.utils.api_stats import ApiStats
from src.utils.datetime_util import DateTimeUtil
from src.formatters import PlayerFormatter, MatchInfoFormatter, YouTubeSectionFormatter
from config import config

logger = logging.getLogger(__name__)

class ReportGenerator:
    WEB_IMAGE_DIR = "public/reports"

    def __init__(self):
        self.player_formatter = PlayerFormatter()
        self.match_info_formatter = MatchInfoFormatter()
        self.youtube_formatter = YouTubeSectionFormatter()
    
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
        if match.competition_logo:
            # 大会名の表示用変換 (Issue #116 Polish)
            competition_display = "Premier League" if match.competition == "EPL" else match.competition
            
            header_html = f'''<div class="match-header-container">
    <img src="{match.competition_logo}" class="competition-logo-header" alt="{match.competition}">
    <div class="match-header-info">
        <h1>{match.home_team} vs {match.away_team}</h1>
        <div class="match-metadata">
            <span class="competition-name">{competition_display}</span>
            <span class="separator">|</span>
            <span class="match-rank">Importance: {match.rank}</span>
        </div>
    </div>
</div>'''
            lines.append(header_html)
        else:
            # フォールバック: ロゴがない場合は従来の表示
            lines.append(f"# {match.home_team} vs {match.away_team}\n")
            lines.append(f"**{match.competition}** / {match.rank}\n")
        
        # 試合レポート本文
        match_report, match_images = self._write_single_match_content(match, youtube_videos)
        lines.append(match_report)
        image_paths.extend(match_images)
        
        # 末尾に選外試合リスト・API使用状況を追加
        lines.append("\n---\n")
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
    
    def _write_single_match_content(self, match: Union[MatchData, MatchAggregate], youtube_videos: Dict[str, List[Dict]]) -> tuple:
        """1試合分のレポート本文を生成"""
        lines = []
        image_paths = []
        
        # 基本情報
        lines.append("### ■ 基本情報")
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
            player_instagram=match.player_instagram
        )
        away_bench_html = self.player_formatter.format_player_cards(
            match.away_bench, "", match.away_team,
            match.player_nationalities, match.player_numbers,
            match.player_birthdates, match.player_photos,
            position_label="SUB", player_positions=match.player_positions,
            player_instagram=match.player_instagram
        )
        
        home_logo_html = f'<img src="{match.home_logo}" alt="{match.home_team}" class="team-logo">' if match.home_logo else ''
        away_logo_html = f'<img src="{match.away_logo}" alt="{match.away_team}" class="team-logo">' if match.away_logo else ''
        
        home_injuries = [i for i in match.injuries_list if i.get("team", "") == match.home_team]
        away_injuries = [i for i in match.injuries_list if i.get("team", "") == match.away_team]
        home_injury_html = self.player_formatter.format_injury_cards(home_injuries, match.player_photos)
        away_injury_html = self.player_formatter.format_injury_cards(away_injuries, match.player_photos)
        
        # ホームチーム
        lines.append(f'<h3 class="lineup-header">{home_logo_html} {match.home_team}（{match.home_formation}）</h3>')
        lines.append("#### Starting XI")
        lines.append(home_cards_html)
        lines.append("#### Substitutes")
        lines.append(home_bench_html)
        lines.append("#### Injuries / Suspended")
        lines.append(home_injury_html)
        
        # アウェイチーム
        lines.append(f'<h3 class="lineup-header">{away_logo_html} {match.away_team}（{match.away_formation}）</h3>')
        lines.append("#### Starting XI")
        lines.append(away_cards_html)
        lines.append("#### Substitutes")
        lines.append(away_bench_html)
        lines.append("#### Injuries / Suspended")
        lines.append(away_injury_html)
        
        home_form = self.match_info_formatter.format_form_with_icons(match.home_recent_form)
        away_form = self.match_info_formatter.format_form_with_icons(match.away_recent_form)
        lines.append(f"- 直近フォーム：Home {home_form} / Away {away_form}")
        lines.append(f"- 過去の対戦成績：{match.h2h_summary}")
        lines.append(f"- 主審：{match.referee}")
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
        if home_img:
            lines.append(f"![{match.home_team}](/reports/{home_img})")
            image_paths.append(f"{self.WEB_IMAGE_DIR}/{home_img}")
        if away_img:
            lines.append(f"![{match.away_team}](/reports/{away_img})")
            image_paths.append(f"{self.WEB_IMAGE_DIR}/{away_img}")
        lines.append("")
        
        # 同国対決（Issue #39）
        if match.same_country_text:
            lines.append("### ■ 同国対決")
            lines.append(f"\n{match.same_country_text}\n")
            lines.append("")
        
        # ニュース・戦術
        lines.append("### ■ ニュース要約（600〜1,000字）")
        lines.append(f"- {match.news_summary}")
        lines.append("")
        
        lines.append("### ■ 戦術プレビュー")
        lines.append(f"- {match.tactical_preview}")
        if match.preview_url and match.preview_url != "https://example.com/tactical-preview":
            lines.append(f"- URL: {match.preview_url}")
        lines.append("")
        
        # 監督セクション
        lines.append("### ■ 監督プレビュー")
        home_manager_photo_html = f'<img src="{match.home_manager_photo}" alt="{match.home_manager}" class="manager-photo">' if match.home_manager_photo else '<div class="manager-photo manager-photo-placeholder">👤</div>'
        away_manager_photo_html = f'<img src="{match.away_manager_photo}" alt="{match.away_manager}" class="manager-photo">' if match.away_manager_photo else '<div class="manager-photo manager-photo-placeholder">👤</div>'
        
        manager_section_html = f'''<div class="manager-section">
<div class="manager-card">
{home_manager_photo_html}
<div class="manager-info">
<div class="manager-team">{match.home_team}</div>
<div class="manager-name">{match.home_manager}</div>
<div class="manager-comment">{match.home_interview}</div>
</div>
</div>
<div class="manager-card">
{away_manager_photo_html}
<div class="manager-info">
<div class="manager-team">{match.away_team}</div>
<div class="manager-name">{match.away_manager}</div>
<div class="manager-comment">{match.away_interview}</div>
</div>
</div>
</div>'''
        lines.append(manager_section_html)
        lines.append("")
        
        # YouTube動画
        match_key = f"{match.home_team} vs {match.away_team}"
        video_data = youtube_videos.get(match_key, {})
        lines.append(self.youtube_formatter.format_youtube_section(video_data, match_key))
        
        # エラーステータス
        lines.append("### ■ エラーステータス")
        lines.append(f"- {match.error_status}")
        lines.append("\n")
        
        return "\n".join(lines), image_paths
