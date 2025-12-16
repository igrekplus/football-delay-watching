"""
国名から国旗絵文字へのマッピング辞書
API-Football が返す国名に対応
"""

# 主要なサッカー選手の国籍マッピング
NATIONALITY_FLAGS = {
    # ヨーロッパ
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Northern Ireland": "🇬🇧",
    "Ireland": "🇮🇪",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Spain": "🇪🇸",
    "Italy": "🇮🇹",
    "Portugal": "🇵🇹",
    "Netherlands": "🇳🇱",
    "Belgium": "🇧🇪",
    "Switzerland": "🇨🇭",
    "Austria": "🇦🇹",
    "Poland": "🇵🇱",
    "Ukraine": "🇺🇦",
    "Croatia": "🇭🇷",
    "Serbia": "🇷🇸",
    "Denmark": "🇩🇰",
    "Sweden": "🇸🇪",
    "Norway": "🇳🇴",
    "Finland": "🇫🇮",
    "Czech Republic": "🇨🇿",
    "Greece": "🇬🇷",
    "Turkey": "🇹🇷",
    "Russia": "🇷🇺",
    "Romania": "🇷🇴",
    "Hungary": "🇭🇺",
    "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮",
    "Bosnia and Herzegovina": "🇧🇦",
    "Albania": "🇦🇱",
    "North Macedonia": "🇲🇰",
    "Montenegro": "🇲🇪",
    "Kosovo": "🇽🇰",
    "Iceland": "🇮🇸",
    "Republic of Ireland": "🇮🇪",
    
    # 南米
    "Brazil": "🇧🇷",
    "Argentina": "🇦🇷",
    "Uruguay": "🇺🇾",
    "Colombia": "🇨🇴",
    "Chile": "🇨🇱",
    "Ecuador": "🇪🇨",
    "Paraguay": "🇵🇾",
    "Peru": "🇵🇪",
    "Venezuela": "🇻🇪",
    "Bolivia": "🇧🇴",
    
    # アフリカ
    "Nigeria": "🇳🇬",
    "Senegal": "🇸🇳",
    "Ghana": "🇬🇭",
    "Ivory Coast": "🇨🇮",
    "Cote D'Ivoire": "🇨🇮",
    "Cameroon": "🇨🇲",
    "Egypt": "🇪🇬",
    "Morocco": "🇲🇦",
    "Algeria": "🇩🇿",
    "Tunisia": "🇹🇳",
    "Mali": "🇲🇱",
    "DR Congo": "🇨🇩",
    "Congo DR": "🇨🇩",
    "South Africa": "🇿🇦",
    "Zimbabwe": "🇿🇼",
    "Guinea": "🇬🇳",
    "Gabon": "🇬🇦",
    "Burkina Faso": "🇧🇫",
    
    # アジア
    "Japan": "🇯🇵",
    "Korea Republic": "🇰🇷",
    "South Korea": "🇰🇷",
    "China": "🇨🇳",
    "Australia": "🇦🇺",
    "Iran": "🇮🇷",
    "Saudi Arabia": "🇸🇦",
    "Qatar": "🇶🇦",
    "UAE": "🇦🇪",
    "United Arab Emirates": "🇦🇪",
    
    # 北中米カリブ海
    "USA": "🇺🇸",
    "United States": "🇺🇸",
    "Mexico": "🇲🇽",
    "Canada": "🇨🇦",
    "Jamaica": "🇯🇲",
    "Costa Rica": "🇨🇷",
    "Panama": "🇵🇦",
    "Honduras": "🇭🇳",
    
    # その他
    "New Zealand": "🇳🇿",
}


def get_flag_emoji(nationality: str) -> str:
    """
    国名から国旗絵文字を取得
    見つからない場合は空文字を返す
    """
    return NATIONALITY_FLAGS.get(nationality, "")


def format_player_with_flag(name: str, nationality: str) -> str:
    """
    選手名と国籍から「選手名 🇫🇷」形式の文字列を生成
    """
    flag = get_flag_emoji(nationality)
    if flag:
        return f"{name} {flag}"
    return name
