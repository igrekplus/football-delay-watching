"""同国対決・キーマッチアップのHTMLフォーマッター"""
import logging
from difflib import SequenceMatcher
from typing import List, Dict
from src.parsers.matchup_parser import PlayerMatchup

logger = logging.getLogger(__name__)

class MatchupFormatter:
    """マッチアップカードのHTMLを生成"""
    
    def format_matchup_section(self, matchups: List[PlayerMatchup], player_photos: Dict[str, str], 
                               team_logos: Dict[str, str], section_title: str = "■ 同国対決") -> str:
        """マッチアップセクション全体のHTMLを生成"""
        if not matchups:
            return ""
            
        html = f'<div class="matchup-section">\n<h3 class="section-title">{section_title}</h3>\n<div class="matchup-container">\n'
        
        for matchup in matchups:
            html += self.format_single_matchup(matchup, player_photos, team_logos)
            
        html += '</div>\n</div>'
        return html

    def _get_photo(self, player_name: str, player_photos: dict) -> str:
        """選手名から写真URLを柔軟に取得（あいまい検索対応）"""
        if not player_name:
            return ""
        
        # 1. 完全一致
        if player_name in player_photos:
            return player_photos[player_name]
        
        # 2. 大文字小文字を無視した完全一致
        name_l = player_name.lower()
        for k, v in player_photos.items():
            if k.lower() == name_l:
                return v
        
        # 3. 部分一致（苗字のみ等に対応）- 短すぎる名前は除外して誤マッチ防止
        if len(name_l) >= 4:
            for k, v in player_photos.items():
                if name_l in k.lower() or k.lower() in name_l:
                    logger.debug(f"Partial match: '{player_name}' -> '{k}'")
                    return v
        
        # 4. 類似度マッチング（70%以上の類似度）
        best_match = None
        best_ratio = 0.0
        for k, v in player_photos.items():
            ratio = SequenceMatcher(None, name_l, k.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (k, v)
        
        if best_match and best_ratio >= 0.7:
            logger.debug(f"Fuzzy match: '{player_name}' -> '{best_match[0]}' (ratio={best_ratio:.2f})")
            return best_match[1]
        
        logger.warning(f"No photo found for player: '{player_name}' (available: {list(player_photos.keys())[:5]}...)")
        return ""

    def _get_logo(self, team_name: str, team_logos: dict) -> str:
        """チーム名からロゴURLを柔軟に取得"""
        if not team_name:
            return ""
        
        # 1. 完全一致
        if team_name in team_logos:
            return team_logos[team_name]
            
        # 2. 部分一致 / 大文字小文字を無視
        name_l = team_name.lower()
        for k, v in team_logos.items():
            k_l = k.lower()
            if name_l in k_l or k_l in name_l:
                return v
        
        logger.debug(f"No logo found for team: '{team_name}'")
        return ""

    def format_single_matchup(self, matchup: PlayerMatchup, player_photos: dict, team_logos: dict) -> str:
        """1つのマッチアップをHTMLカードとしてフォーマット"""
        p1_photo = self._get_photo(matchup.player1_name, player_photos)
        p2_photo = self._get_photo(matchup.player2_name, player_photos)
        
        p1_logo = self._get_logo(matchup.player1_team, team_logos)
        p2_logo = self._get_logo(matchup.player2_team, team_logos)
        
        # ヘッダーを表示（空でない場合）
        header_html = f'<div class="matchup-country-header">{matchup.header}</div>' if matchup.header else ""
        
        return f'''
<div class="matchup-country">
    <div class="matchup-header-row">
        {header_html}
        <div class="matchup-players">
            <div class="matchup-player-item">
                <div class="matchup-photo-wrapper">
                    <img src="{p1_photo}" alt="{matchup.player1_name}" class="matchup-photo" onerror="this.style.opacity=\'0.3\';">
                    <img src="{p1_logo}" alt="{matchup.player1_team}" class="matchup-badge" onerror="this.style.display=\'none\';">
                </div>
                <div class="matchup-player-info">
                    <div class="matchup-player-name">{matchup.player1_name}</div>
                    <div class="matchup-team-name">{matchup.player1_team}</div>
                </div>
            </div>
            <div class="matchup-player-item">
                <div class="matchup-photo-wrapper">
                    <img src="{p2_photo}" alt="{matchup.player2_name}" class="matchup-photo" onerror="this.style.opacity=\'0.3\';">
                    <img src="{p2_logo}" alt="{matchup.player2_team}" class="matchup-badge" onerror="this.style.display=\'none\';">
                </div>
                <div class="matchup-player-info">
                    <div class="matchup-player-name">{matchup.player2_name}</div>
                    <div class="matchup-team-name">{matchup.player2_team}</div>
                </div>
            </div>
        </div>
    </div>
    <div class="matchup-description">
        {matchup.description}
    </div>
</div>
'''
