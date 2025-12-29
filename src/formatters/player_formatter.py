"""
Player formatting utilities for report generation.
"""
from typing import List, Dict
from datetime import datetime
from src.utils.nationality_flags import format_player_with_flag


class PlayerFormatter:
    """選手情報のフォーマット処理を担当するクラス"""
    
    def format_lineup_by_position(self, lineup: List[str], formation: str, team_name: str, 
                                   nationalities: Dict[str, str] = None, 
                                   player_numbers: Dict[str, int] = None,
                                   player_birthdates: Dict[str, str] = None) -> str:
        """
        フォーメーション情報を元に選手をポジション別に振り分けて表示
        例: 4-3-3 -> GK:1, DF:4, MF:3, FW:3
        国籍情報がある場合は国旗絵文字を追加
        背番号がある場合は先頭に表示
        生年月日がある場合は (YYYY/MM/DD) 形式で表示
        """
        if nationalities is None:
            nationalities = {}
        if player_numbers is None:
            player_numbers = {}
        if player_birthdates is None:
            player_birthdates = {}
            
        def format_birthdate(date_str: str) -> str:
            """YYYY-MM-DD を YYYY/MM/DD に変換"""
            if not date_str:
                return ""
            try:
                return date_str.replace('-', '/')
            except Exception:
                return ""
            
        def format_player(name: str) -> str:
            nationality = nationalities.get(name, "")
            number = player_numbers.get(name)
            birthdate = player_birthdates.get(name, "")
            formatted = format_player_with_flag(name, nationality)
            if number is not None:
                formatted = f"#{number} {formatted}"
            if birthdate:
                formatted = f"{formatted} ({format_birthdate(birthdate)})"
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

    def calculate_age(self, birthdate_str: str) -> int:
        """生年月日から年齢を計算"""
        if not birthdate_str:
            return None
        try:
            import pytz
            birth = datetime.strptime(birthdate_str, "%Y-%m-%d")
            jst = pytz.timezone('Asia/Tokyo')
            today = datetime.now(jst).replace(tzinfo=None)
            age = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            return age
        except Exception:
            return None

    def get_player_position(self, index: int, lineup_size: int, formation: str) -> str:
        """選手のインデックスとフォーメーションからポジションを決定"""
        if index == 0:
            return "GK"
        
        # フォーメーションをパース（例: "4-3-3" -> [4, 3, 3]）
        try:
            parts = [int(x) for x in formation.split('-')]
        except (ValueError, AttributeError):
            return "FW"  # パース失敗時
        
        position_names = ['DF', 'MF', 'FW']
        outfield_index = index - 1  # GKを除いたインデックス
        
        cumulative = 0
        for i, count in enumerate(parts):
            cumulative += count
            if outfield_index < cumulative:
                return position_names[i] if i < len(position_names) else 'FW'
        
        return 'FW'

    def format_player_cards(self, lineup: List[str], formation: str, team_name: str,
                             nationalities: Dict[str, str] = None,
                             player_numbers: Dict[str, int] = None,
                             player_birthdates: Dict[str, str] = None,
                             player_photos: Dict[str, str] = None,
                             position_label: str = None,
                             player_positions: Dict[str, str] = None,
                             player_instagram: Dict[str, str] = None) -> str:
        """
        選手リストをカード形式のHTMLに変換
        
        Args:
            position_label: 全選手に使用するポジションラベル（例: "SUB"）。
                           Noneの場合はフォーメーションから計算
            player_positions: 選手名 -> ポジションのマッピング（ベンチ用）
            player_instagram: 選手名 -> Instagram URLのマッピング
        """
        if nationalities is None:
            nationalities = {}
        if player_numbers is None:
            player_numbers = {}
        if player_birthdates is None:
            player_birthdates = {}
        if player_photos is None:
            player_photos = {}
        if player_positions is None:
            player_positions = {}
        if player_instagram is None:
            player_instagram = {}
        
        if not lineup:
            return '<div class="player-cards"><p>選手情報なし</p></div>'
        
        # ポジション略称からフル名への変換
        pos_map = {'G': 'GK', 'D': 'DF', 'M': 'MF', 'F': 'FW'}
        
        # Instagram SVGアイコン
        instagram_svg = '''<svg class="player-instagram-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>'''
        
        cards_html = []
        for idx, name in enumerate(lineup):
            # ベンチ選手の場合: player_positionsから取得、なければposition_labelを使用
            if position_label:
                api_pos = player_positions.get(name, '')
                position = pos_map.get(api_pos, api_pos) if api_pos else position_label
            else:
                position = self.get_player_position(idx, len(lineup), formation)
            
            number = player_numbers.get(name)
            nationality = nationalities.get(name, "")
            birthdate = player_birthdates.get(name, "")
            photo_url = player_photos.get(name, "")
            instagram_url = player_instagram.get(name, "")
            age = self.calculate_age(birthdate)
            
            # 国旗を取得
            flag = format_player_with_flag("", nationality).strip() if nationality else ""
            
            # Issue #51: カードHTML構造を改善
            number_display = f"#{number}" if number is not None else ""
            photo_html = f'<img src="{photo_url}" alt="{name}" class="player-card-photo">' if photo_url else '<div class="player-card-photo player-card-photo-placeholder"></div>'
            # 年齢と生年月日を併記
            birthdate_formatted = birthdate.replace('-', '/') if birthdate else ""
            age_display = f"{age}歳" if age else ""
            if birthdate_formatted and age_display:
                age_display = f"{age_display} ({birthdate_formatted})"
            # 国籍に国旗を追加
            nationality_display = f"{flag} {nationality}" if nationality else ""
            
            # Issue #40: Instagramリンク
            instagram_html = ""
            if instagram_url:
                instagram_html = f'<a href="{instagram_url}" target="_blank" rel="noopener noreferrer" class="player-instagram-link" title="Instagram">{instagram_svg}</a>'
            
            card = f'''<div class="player-card">
<div class="player-card-header"><span>{name}</span>{instagram_html}</div>
<div class="player-card-body">
{photo_html}
<div class="player-card-info">
<div class="player-card-position">{position} {number_display}</div>
<div class="player-card-nationality">{nationality_display}</div>
<div class="player-card-age">{age_display}</div>
</div>
</div>
</div>'''
            cards_html.append(card)
        
        return f'<div class="player-cards">\n' + '\n'.join(cards_html) + '\n</div>'

    def format_injury_cards(self, injuries_list: list, player_photos: Dict[str, str] = None) -> str:
        """
        怪我人・出場停止リストをカード形式のHTMLに変換
        """
        if not injuries_list:
            return '<div class="player-cards"><p>なし</p></div>'
        
        if player_photos is None:
            player_photos = {}
        
        cards_html = []
        for injury in injuries_list:
            name = injury.get("name", "Unknown")
            team = injury.get("team", "")
            reason = injury.get("reason", "")
            # injuries_list 内の photo を優先、なければ player_photos から取得
            photo_url = injury.get("photo", "") or player_photos.get(name, "")
            
            photo_html = f'<img src="{photo_url}" alt="{name}" class="player-card-photo">' if photo_url else '<div class="player-card-photo player-card-photo-placeholder"></div>'
            
            card = f'''<div class="player-card injury-card">
<div class="player-card-header"><span>{name}</span></div>
<div class="player-card-body">
{photo_html}
<div class="player-card-info">
<div class="player-card-position">🏥 OUT</div>
<div class="player-card-nationality">{team}</div>
<div class="player-card-age injury-reason">⚠️ {reason}</div>
</div>
</div>
</div>'''
            cards_html.append(card)
        
        return f'<div class="player-cards">\n' + '\n'.join(cards_html) + '\n</div>'
