"""同国対決・キーマッチアップのHTMLフォーマッター"""
from typing import List, Dict
from src.parsers.matchup_parser import PlayerMatchup

class MatchupFormatter:
    """マッチアップカードのHTMLを生成"""
    
    def format_matchup_section(
        self,
        matchups: List[PlayerMatchup],
        player_photos: Dict[str, str],
        team_logos: Dict[str, str],
        section_title: str = "■ 同国対決"
    ) -> str:
        """
        マッチアップセクション全体のHTMLを生成
        
        Args:
            matchups: PlayerMatchup のリスト
            player_photos: {選手名: 画像URL}
            team_logos: {チーム名: ロゴURL}
            section_title: セクションタイトル
            
        Returns:
            HTML文字列
        """
        if not matchups:
            return ""
        
        countries_html = []
        for matchup in matchups:
            country_html = self._format_country_section(
                matchup, player_photos, team_logos
            )
            countries_html.append(country_html)
        
        return f"""
        <div class="matchup-section">
            <h3 class="section-title">{section_title}</h3>
            <div class="matchup-container">
                {''.join(countries_html)}
            </div>
        </div>
        """
    
    def _format_country_section(
        self,
        matchup: PlayerMatchup,
        player_photos: Dict[str, str],
        team_logos: Dict[str, str]
    ) -> str:
        """1つの国セクションのHTMLを生成"""
        
        # 画像URLを取得
        p1_photo = player_photos.get(matchup.player1_name, "")
        p2_photo = player_photos.get(matchup.player2_name, "")
        p1_logo = team_logos.get(matchup.player1_team, "")
        p2_logo = team_logos.get(matchup.player2_team, "")
        
        return f"""
        <div class="matchup-country">
            <div class="matchup-country-header">
                {matchup.country_flag} {matchup.country}
            </div>
            <div class="matchup-players">
                <div class="matchup-player-item">
                    <div class="matchup-photo-wrapper">
                        <img src="{p1_photo}" alt="{matchup.player1_name}" class="matchup-photo" onerror="this.style.opacity='0.3';">
                        <img src="{p1_logo}" alt="{matchup.player1_team}" class="matchup-badge" onerror="this.style.display='none';">
                    </div>
                    <div class="matchup-player-info">
                        <div class="matchup-player-name">{matchup.player1_name}</div>
                        <div class="matchup-team-name">{matchup.player1_team}</div>
                    </div>
                </div>
                <div class="matchup-player-item">
                    <div class="matchup-photo-wrapper">
                        <img src="{p2_photo}" alt="{matchup.player2_name}" class="matchup-photo" onerror="this.style.opacity='0.3';">
                        <img src="{p2_logo}" alt="{matchup.player2_team}" class="matchup-badge" onerror="this.style.display='none';">
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
        """
