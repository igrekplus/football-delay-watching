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
        """1つのマッチアップをHTMLカードとしてフォーマット（最大4名対応）"""
        header_html = f'<div class="matchup-country-header">{matchup.header}</div>' if matchup.header else ""
        
        players_html = ""
        for player_name, player_team in matchup.players:
            photo = self._get_photo(player_name, player_photos)
            logo = self._get_logo(player_team, team_logos)
            
            if photo:
                photo_html = f'<img src="{photo}" alt="{player_name}" class="matchup-photo" onerror="this.style.opacity=\'0.3\';">'
            else:
                photo_html = '<div class="matchup-photo-placeholder"></div>'
                
            players_html += f'''
            <div class="matchup-player-item">
                <div class="matchup-photo-wrapper">
                    {photo_html}
                    <img src="{logo}" alt="{player_team}" class="matchup-badge" onerror="this.style.display=\'none\';">
                </div>
                <div class="matchup-player-info">
                    <div class="matchup-player-name">{player_name}</div>
                    <div class="matchup-team-name">{player_team}</div>
                </div>
            </div>
            '''
            
        return f'''
<div class="matchup-country">
    <div class="matchup-header-row">
        {header_html}
        <div class="matchup-players">
            {players_html}
        </div>
    </div>
    <div class="matchup-description">
        {matchup.description}
    </div>
</div>
'''

    def format_key_player_section(self, key_players: List, player_photos: Dict[str, str], 
                                  team_logos: Dict[str, str], section_title: str = "■ 注目選手") -> str:
        """キープレイヤーセクション全体のHTMLを生成"""
        if not key_players:
            return ""
            
        html = f'<div class="matchup-section key-player-section">\n<h3 class="section-title">{section_title}</h3>\n<div class="matchup-container">\n'
        
        for player in key_players:
            html += self.format_single_key_player(player, player_photos, team_logos)
            
        html += '</div>\n</div>'
        return html

    def format_single_key_player(self, player, player_photos: dict, team_logos: dict) -> str:
        """1人のキープレイヤーをHTMLカードとしてフォーマット"""
        from src.parsers.key_player_parser import KeyPlayer
        
        photo = self._get_photo(player.name, player_photos)
        logo = self._get_logo(player.team, team_logos)
        
        details_html = ""
        if player.detailed_description:
            # 改行を<br>に変換
            formatted_details = player.detailed_description.replace('\n', '<br>')
            details_html = f'''
            <details class="key-player-details">
                <summary>詳細を見る</summary>
                <div class="key-player-details-content">
                    {formatted_details}
                </div>
            </details>
            '''
        
        # Generate photo HTML: use placeholder if no photo URL
        if photo:
            photo_html = f'<img src="{photo}" alt="{player.name}" class="matchup-photo" onerror="this.style.opacity=\'0.3\';">'
        else:
            photo_html = '<div class="matchup-photo-placeholder"></div>'
        
        return f'''
<div class="matchup-country key-player-card">
    <div class="matchup-header-row">
        <div class="matchup-player-item">
            <div class="matchup-photo-wrapper">
                {photo_html}
                <img src="{logo}" alt="{player.team}" class="matchup-badge" onerror="this.style.display=\'none\';">
            </div>
            <div class="matchup-player-info">
                <div class="matchup-player-name">{player.name}</div>
                <div class="matchup-team-name">{player.team}</div>
            </div>
        </div>
    </div>
    <div class="matchup-description">
        {player.description}
        {details_html}
    </div>
</div>
'''

    def format_tactical_style_section(self, tactical_styles: List, team_logos: Dict[str, str], 
                                     section_title: str = "🎯 戦術スタイル") -> str:
        """戦術スタイルセクション全体のHTMLを生成"""
        if not tactical_styles:
            return ""
            
        html = f'<div class="matchup-section tactical-style-section">\n<h3 class="section-title">{section_title}</h3>\n<div class="matchup-container">\n'
        
        for style in tactical_styles:
            html += self.format_single_tactical_style(style, team_logos)
            
        html += '</div>\n</div>'
        return html

    def format_single_tactical_style(self, style, team_logos: dict) -> str:
        """1チームの戦術スタイルをHTMLカードとしてフォーマット"""
        logo = self._get_logo(style.team, team_logos)
        
        # description内のMarkdown的な箇条書きを一部調整（簡易変換）
        formatted_desc = style.description.replace('\n- ', '<br>• ').replace('\n* ', '<br>• ')
        if formatted_desc.startswith('- '):
            formatted_desc = '• ' + formatted_desc[2:]
        elif formatted_desc.startswith('* '):
            formatted_desc = '• ' + formatted_desc[2:]
        formatted_desc = formatted_desc.replace('\n', '<br>')

        return f'''
<div class="matchup-country tactical-style-card">
    <div class="matchup-header-row">
        <div class="matchup-player-item">
            <div class="matchup-photo-wrapper">
                <img src="{logo}" alt="{style.team}" class="matchup-badge" style="width: 48px; height: 48px;" onerror="this.style.display=\'none\';">
            </div>
            <div class="matchup-player-info">
                <div class="matchup-player-name">{style.team}</div>
            </div>
        </div>
    </div>
    <div class="matchup-description">
        {formatted_desc}
    </div>
</div>
'''
