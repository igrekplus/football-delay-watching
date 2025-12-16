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

    def _format_lineup_by_position(self, lineup: List[str], formation: str, team_name: str, 
                                     nationalities: Dict[str, str] = None, 
                                     player_numbers: Dict[str, int] = None) -> str:
        """
        フォーメーション情報を元に選手をポジション別に振り分けて表示
        例: 4-3-3 -> GK:1, DF:4, MF:3, FW:3
        国籍情報がある場合は国旗絵文字を追加
        背番号がある場合は先頭に表示
        """
        if nationalities is None:
            nationalities = {}
        if player_numbers is None:
            player_numbers = {}
            
        def format_player(name: str) -> str:
            nationality = nationalities.get(name, "")
            number = player_numbers.get(name)
            formatted = format_player_with_flag(name, nationality)
            if number is not None:
                formatted = f"#{number} {formatted}"
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

    def generate(self, matches: List[MatchData]) -> tuple:
        """
        Generates markdown report string
        
        Returns:
            tuple: (report_content: str, image_paths: List[str])
        """
        lines = []
        image_paths = []  # 生成された画像パスを収集
        
        lines.append(self._write_header(matches))
        report_lines, report_images = self._write_match_reports(matches)
        lines.append(report_lines)
        image_paths.extend(report_images)
        lines.append(self._write_excluded_list(matches))
        
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

    def _write_match_reports(self, matches: List[MatchData]) -> tuple:
        """
        試合レポートを生成
        
        Returns:
            tuple: (report_string: str, image_paths: List[str])
        """
        lines = []
        image_paths = []
        target_matches = [m for m in matches if m.is_target]
        
        for i, match in enumerate(target_matches, 1):
            lines.append(f"## 試合{i}：{match.home_team} vs {match.away_team} （{match.competition}／{match.rank}）\n")
            
            lines.append("### ■ 基本情報（固定情報）")
            lines.append(f"- 大会：{match.competition}")
            lines.append(f"- 日時：{match.kickoff_jst} / {match.kickoff_local}")
            lines.append(f"- 会場：{match.venue}")
            
            # ポジション別スタメン表示（国籍情報・背番号付き）
            home_lineup_formatted = self._format_lineup_by_position(
                match.home_lineup, match.home_formation, match.home_team, 
                match.player_nationalities, match.player_numbers
            )
            away_lineup_formatted = self._format_lineup_by_position(
                match.away_lineup, match.away_formation, match.away_team, 
                match.player_nationalities, match.player_numbers
            )
            lines.append(f"- スタメン（{match.home_team}）：")
            lines.append(f"    - {home_lineup_formatted}")
            lines.append(f"- スタメン（{match.away_team}）：")
            lines.append(f"    - {away_lineup_formatted}")
            
            lines.append(f"- ベンチ（Home）：{', '.join(match.home_bench)}")
            lines.append(f"- ベンチ（Away）：{', '.join(match.away_bench)}")
            lines.append(f"- フォーメーション：Home {match.home_formation} / Away {match.away_formation}")
            lines.append(f"- 出場停止・負傷者情報：{match.injuries_info}")
            
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
            
            # Generate formation diagrams
            lines.append("### ■ フォーメーション図")
            home_img = generate_formation_image(
                match.home_formation, match.home_lineup, match.home_team,
                is_home=True, output_dir=config.OUTPUT_DIR, match_id=match.id,
                player_numbers=match.player_numbers
            )
            away_img = generate_formation_image(
                match.away_formation, match.away_lineup, match.away_team,
                is_home=False, output_dir=config.OUTPUT_DIR, match_id=match.id,
                player_numbers=match.player_numbers
            )
            if home_img:
                lines.append(f"![{match.home_team}]({home_img})")
                image_paths.append(home_img)
            if away_img:
                lines.append(f"![{match.away_team}]({away_img})")
                image_paths.append(away_img)
            lines.append("")
            
            # Player photos section (if available)
            if match.player_photos:
                lines.append("### ■ 選手画像")
                
                def format_photo_caption(name: str) -> str:
                    """画像キャプションに背番号を追加"""
                    number = match.player_numbers.get(name)
                    if number is not None:
                        return f"{name}[#{number}]"
                    return name
                
                # Home team photos
                home_photos = [
                    f"![{format_photo_caption(name)}]({match.player_photos[name]})" 
                    for name in match.home_lineup 
                    if name in match.player_photos
                ]
                if home_photos:
                    lines.append(f"**{match.home_team}**")
                    lines.append(" ".join(home_photos))
                
                # Away team photos
                away_photos = [
                    f"![{format_photo_caption(name)}]({match.player_photos[name]})" 
                    for name in match.away_lineup 
                    if name in match.player_photos
                ]
                if away_photos:
                    lines.append(f"**{match.away_team}**")
                    lines.append(" ".join(away_photos))
                lines.append("")
            
            lines.append("### ■ ニュース要約（600〜1,000字）")
            lines.append(f"- {match.news_summary}")
            lines.append("")
            
            lines.append("### ■ 戦術プレビュー")
            lines.append(f"- {match.tactical_preview}")
            lines.append(f"- URL: {match.preview_url}")
            lines.append("")
            
            lines.append("### ■ 監督・選手コメント")
            lines.append(f"- {match.home_interview}")
            lines.append(f"- {match.away_interview}")
            lines.append("")
            
            lines.append("### ■ エラーステータス")
            lines.append(f"- {match.error_status}")
            lines.append("\n")
            
        return "\n".join(lines), image_paths

    def _write_excluded_list(self, matches: List[MatchData]) -> str:
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
        
        # Append execution timestamp
        import pytz
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"\n---\n*レポート生成日時: {now_jst} JST*")
            
        return "\n".join(lines)
