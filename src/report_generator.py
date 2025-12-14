from datetime import datetime
from typing import List
from .match_processor import MatchData
import logging
from .spoiler_filter import SpoilerFilter
from .formation_image import generate_formation_image
from config import config

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        pass

    def generate(self, matches: List[MatchData]) -> str:
        # Generates markdown report string
        lines = []
        lines.append(self._write_header(matches))
        lines.append(self._write_match_reports(matches))
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
        return report

    def _write_header(self, matches: List[MatchData]) -> str:
        target_matches = [m for m in matches if m.is_target]
        lines = [f"# 本日の対象試合（{len(target_matches)}件）\n"]
        for i, match in enumerate(target_matches, 1):
            lines.append(f"{i}. {match.home_team} vs {match.away_team} （{match.competition}／{match.rank}）")
        lines.append("\n")
        return "\n".join(lines)

    def _write_match_reports(self, matches: List[MatchData]) -> str:
        lines = []
        target_matches = [m for m in matches if m.is_target]
        
        for i, match in enumerate(target_matches, 1):
            lines.append(f"## 試合{i}：{match.home_team} vs {match.away_team} （{match.competition}／{match.rank}）\n")
            
            lines.append("### ■ 基本情報（固定情報）")
            lines.append(f"- 大会：{match.competition}")
            lines.append(f"- 日時：{match.kickoff_jst} / {match.kickoff_local}")
            lines.append(f"- 会場：{match.venue}")
            lines.append(f"- スタメン（Home）：{', '.join(match.home_lineup)}")
            lines.append(f"- スタメン（Away）：{', '.join(match.away_lineup)}")
            lines.append(f"- ベンチ（Home）：{', '.join(match.home_bench)}")
            lines.append(f"- ベンチ（Away）：{', '.join(match.away_bench)}")
            lines.append(f"- フォーメーション：Home {match.home_formation} / Away {match.away_formation}")
            lines.append(f"- 出場停止・負傷者情報：{match.injuries_info}")
            lines.append(f"- 直近フォーム：Home {match.home_recent_form} / Away {match.away_recent_form}")
            lines.append(f"- 過去の対戦成績：{match.h2h_summary}")
            lines.append(f"- 主審：{match.referee}")
            lines.append("")
            
            # Generate formation diagrams
            lines.append("### ■ フォーメーション図")
            home_img = generate_formation_image(
                match.home_formation, match.home_lineup, match.home_team,
                is_home=True, output_dir=config.OUTPUT_DIR, match_id=match.id
            )
            away_img = generate_formation_image(
                match.away_formation, match.away_lineup, match.away_team,
                is_home=False, output_dir=config.OUTPUT_DIR, match_id=match.id
            )
            if home_img:
                lines.append(f"![{match.home_team}]({home_img})")
            if away_img:
                lines.append(f"![{match.away_team}]({away_img})")
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
            
        return "\n".join(lines)

    def _write_excluded_list(self, matches: List[MatchData]) -> str:
        lines = ["## 選外試合リスト\n"]
        excluded = [m for m in matches if not m.is_target]
        if not excluded:
            lines.append("- なし")
        for match in excluded:
            lines.append(f"- {match.home_team} vs {match.away_team} （{match.competition}）… {match.selection_reason}")
            
        # Append API Quota Info
        if config.QUOTA_INFO:
            lines.append("\n## API使用状況")
            for key, info in config.QUOTA_INFO.items():
                lines.append(f"- {key}: {info}")
            # Static note for Google APIs
            lines.append("- Google Custom Search API: Check Cloud Console (Quota: 100/day free)")
            
        return "\n".join(lines)
