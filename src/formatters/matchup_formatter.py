"""同国対決・キーマッチアップのHTMLフォーマッター"""
from typing import List, Dict
from src.parsers.matchup_parser import PlayerMatchup

class MatchupFormatter:
    """マッチアップカードのHTMLを生成"""
    
    def format_matchup_section(self, matchups: List[PlayerMatchup], player_photos: Dict[str, str], 
                               team_logos: Dict[str, str], section_title: str = "■ 同国対決") -> str:
        """マッチアップセクション全体のHTMLを生成"""
        if not matchups:
            return ""
            
        html = f'<div class="matchup-section">\n<h3 class="section-title">{section_title}</h3>\n<div class="matchup-container">\n'
        
        for matchup in matchups:
            html += self.format_matchup_card(matchup, player_photos, team_logos)
            
        html += '</div>\n</div>'
        return html

    def format_matchup_card(self, matchup: PlayerMatchup, player_photos: Dict[str, str], 
                            team_logos: Dict[str, str]) -> str:
        """個別の対決カードのHTMLを生成"""
        p1_photo = player_photos.get(matchup.player1_name, "")
        p2_photo = player_photos.get(matchup.player2_name, "")
        
        p1_logo = team_logos.get(matchup.player1_team, "")
        p2_logo = team_logos.get(matchup.player2_team, "")
        
        # ヘッダーを表示（空でない場合）
        header_html = f'<div class="matchup-country-header">{matchup.header}</div>' if matchup.header else ""
        
        return f'''
<div class="matchup-country">
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
    <div class="matchup-description">
        {matchup.description}
    </div>
</div>
'''
