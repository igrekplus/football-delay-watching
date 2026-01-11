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
            birth = datetime.strptime(birthdate_str, "%Y-%m-%d")
            # DateTimeUtilを使って現在時刻(JST)を取得し、tzinfoを削除して比較（生年月日がnaiveなため）
            from src.utils.datetime_util import DateTimeUtil
            today = DateTimeUtil.now_jst().replace(tzinfo=None)
            
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

    def _sanitize_photo_url(self, url: str) -> str:
        """
        画像URLをクリーンアップする。
        "NO PHOTO YET" などの無効な文字列を空文字に変換し、プレースホルダーが表示されるようにする。
        """
        if not url:
            return ""
        
        invalid_markers = ["no photo yet", "null", "none"]
        if url.lower().strip() in invalid_markers:
            return ""
            
        return url

    def format_player_cards(self, lineup: List[str], formation: str, team_name: str,
                             nationalities: Dict[str, str] = None,
                             player_numbers: Dict[str, int] = None,
                             player_birthdates: Dict[str, str] = None,
                             player_photos: Dict[str, str] = None,
                             position_label: str = None,
                             player_positions: Dict[str, str] = None,
                             player_instagram: Dict[str, str] = None,
                             css_class: str = "player-cards") -> str:
        """
        選手リストをカード形式のHTMLに変換
        """
        from src.template_engine import render_template
        
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
            return f'<div class="{css_class}"><p>選手情報なし</p></div>'
        
        # ポジション略称からフル名への変換
        pos_map = {'G': 'GK', 'D': 'DF', 'M': 'MF', 'F': 'FW'}
        
        players_data = []
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
            photo_url = self._sanitize_photo_url(player_photos.get(name, ""))
            instagram_url = player_instagram.get(name, "")
            age = self.calculate_age(birthdate)
            
            # 国旗を取得
            flag = format_player_with_flag("", nationality).strip() if nationality else ""
            
            # 表示用データの整理
            number_display = f"#{number}" if number is not None else ""
            birthdate_formatted = birthdate.replace('-', '/') if birthdate else ""
            age_display = f"{age}歳" if age else ""
            if birthdate_formatted and age_display:
                age_display = f"{age_display} ({birthdate_formatted})"
            
            players_data.append({
                "name": name,
                "position": position,
                "number_display": number_display,
                "nationality": nationality,
                "flag": flag,
                "age_display": age_display,
                "photo_url": photo_url,
                "instagram_url": instagram_url
            })
        
        return render_template("partials/player_card.html", 
                               css_class=css_class, 
                               players=players_data)

    def format_injury_cards(self, injuries_list: list, player_photos: Dict[str, str] = None, css_class: str = "player-cards") -> str:
        """
        怪我人・出場停止リストをカード形式のHTMLに変換
        """
        from src.template_engine import render_template
        
        if not injuries_list:
            return f'<div class="{css_class}"><p>なし</p></div>'
        
        if player_photos is None:
            player_photos = {}
        
        injuries_data = []
        for injury in injuries_list:
            name = injury.get("name", "Unknown")
            team = injury.get("team", "")
            reason = injury.get("reason", "")
            raw_photo_url = injury.get("photo", "") or player_photos.get(name, "")
            photo_url = self._sanitize_photo_url(raw_photo_url)
            
            injuries_data.append({
                "name": name,
                "team": team,
                "reason": reason,
                "photo_url": photo_url
            })
        
        return render_template("partials/injury_card.html", 
                               css_class=css_class, 
                               injuries=injuries_data)
