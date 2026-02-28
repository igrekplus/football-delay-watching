import html

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
    "Republic of Ireland": "🇮🇪",
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
    "Bosnia & Herzegovina": "🇧🇦",
    "Albania": "🇦🇱",
    "North Macedonia": "🇲🇰",
    "Montenegro": "🇲🇪",
    "Kosovo": "🇽🇰",
    "Iceland": "🇮🇸",
    "Bulgaria": "🇧🇬",
    "Cyprus": "🇨🇾",
    "Georgia": "🇬🇪",
    "Belarus": "🇧🇾",
    "Moldova": "🇲🇩",
    "Estonia": "🇪🇪",
    "Latvia": "🇱🇻",
    "Lithuania": "🇱🇹",
    "Luxembourg": "🇱🇺",
    "Malta": "🇲🇹",
    "Andorra": "🇦🇩",
    "San Marino": "🇸🇲",
    "Gibraltar": "🇬🇮",
    "Liechtenstein": "🇱🇮",
    "Faroe Islands": "🇫🇴",
    "Armenia": "🇦🇲",
    "Azerbaijan": "🇦🇿",
    "Kazakhstan": "🇰🇿",
    "Israel": "🇮🇱",
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
    "Suriname": "🇸🇷",
    "Guyana": "🇬🇾",
    # 北中米カリブ海
    "USA": "🇺🇸",
    "United States": "🇺🇸",
    "Mexico": "🇲🇽",
    "Canada": "🇨🇦",
    "Jamaica": "🇯🇲",
    "Costa Rica": "🇨🇷",
    "Panama": "🇵🇦",
    "Honduras": "🇭🇳",
    "El Salvador": "🇸🇻",
    "Guatemala": "🇬🇹",
    "Nicaragua": "🇳🇮",
    "Trinidad and Tobago": "🇹🇹",
    "Trinidad & Tobago": "🇹🇹",
    "Haiti": "🇭🇹",
    "Curacao": "🇨🇼",
    "Cuba": "🇨🇺",
    "Dominican Republic": "🇩🇴",
    "Grenada": "🇬🇩",
    "Barbados": "🇧🇧",
    "Saint Kitts and Nevis": "🇰🇳",
    "Saint Lucia": "🇱🇨",
    "Antigua and Barbuda": "🇦🇬",
    "Bermuda": "🇧🇲",
    "Belize": "🇧🇿",
    "Martinique": "🇲🇶",
    "Guadeloupe": "🇬🇵",
    # アフリカ
    "Nigeria": "🇳🇬",
    "Senegal": "🇸🇳",
    "Ghana": "🇬🇭",
    "Ivory Coast": "🇨🇮",
    "Cote D'Ivoire": "🇨🇮",
    "Côte d'Ivoire": "🇨🇮",
    "Cameroon": "🇨🇲",
    "Egypt": "🇪🇬",
    "Morocco": "🇲🇦",
    "Algeria": "🇩🇿",
    "Tunisia": "🇹🇳",
    "Mali": "🇲🇱",
    "DR Congo": "🇨🇩",
    "Congo DR": "🇨🇩",
    "Democratic Republic of the Congo": "🇨🇩",
    "South Africa": "🇿🇦",
    "Zimbabwe": "🇿🇼",
    "Guinea": "🇬🇳",
    "Gabon": "🇬🇦",
    "Burkina Faso": "🇧🇫",
    "Angola": "🇦🇴",
    "Zambia": "🇿🇲",
    "Gambia": "🇬🇲",
    "Benin": "🇧🇯",
    "Cape Verde": "🇨🇻",
    "Congo": "🇨🇬",
    "Equatorial Guinea": "🇬🇶",
    "Guinea-Bissau": "🇬🇼",
    "Mozambique": "🇲🇿",
    "Sierra Leone": "🇸🇱",
    "Togo": "🇹🇬",
    "Liberia": "🇱🇷",
    "Namibia": "🇳🇦",
    "Tanzania": "🇹🇿",
    "Kenya": "🇰🇪",
    "Uganda": "🇺🇬",
    "Madagascar": "🇲🇬",
    "Mauritania": "🇲🇷",
    "Sudan": "🇸🇩",
    "Libya": "🇱🇾",
    "Comoros": "🇰🇲",
    "Central African Republic": "🇨🇫",
    "Burundi": "🇧🇮",
    "Ethiopia": "🇪🇹",
    "Rwanda": "🇷🇼",
    "Malawi": "🇲🇼",
    # アジア・オセアニア
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
    "Iraq": "🇮🇶",
    "Uzbekistan": "🇺🇿",
    "Thailand": "🇹🇭",
    "Vietnam": "🇻🇳",
    "Indonesia": "🇮🇩",
    "Malaysia": "🇲🇾",
    "Philippines": "🇵🇭",
    "Jordan": "🇯🇴",
    "Oman": "🇴🇲",
    "Bahrain": "🇧🇭",
    "Syria": "🇸🇾",
    "Lebanon": "🇱🇧",
    "Palestine": "🇵🇸",
    "Kuwait": "🇰🇼",
    "India": "🇮🇳",
    "Kyrgyzstan": "🇰🇬",
    "Tajikistan": "🇹🇯",
    "Turkmenistan": "🇹🇲",
    # API-Football specific names (hyphenated) and variations
    "South-Korea": "🇰🇷",
    "Saudi-Arabia": "🇸🇦",
    "New-Zealand": "🇳🇿",
    "Costa-Rica": "🇨🇷",
    "United-Arab-Emirates": "🇦🇪",
    "South-Africa": "🇿🇦",
    "Czech-Republic": "🇨🇿",
    "Dominican-Republic": "🇩🇴",
    "El-Salvador": "🇸🇻",
    "Faroe-Islands": "🇫🇴",
    "Trinidad-And-Tobago": "🇹🇹",
    "Antigua-And-Barbuda": "🇦🇬",
    "Burkina-Faso": "🇧🇫",
    "Congo-DR": "🇨🇩",
    "Ivory-Coast": "🇨🇮",
    "Hong-Kong": "🇭🇰",
    "Chinese-Taipei": "🇹🇼",
    "Bosnia": "🇧🇦",
    "Macedonia": "🇲🇰",
}

FLAGCDN_SPECIAL_CODES = {
    "England": "gb-eng",
    "Scotland": "gb-sct",
    "Wales": "gb-wls",
    "Northern Ireland": "gb-nir",
}


def get_flag_emoji(nationality: str) -> str:
    """
    国名から国旗絵文字を取得
    見つからない場合は空文字を返す
    """
    if not nationality:
        return ""

    # HTMLエスケープ文字をデコード (例: "Cote D&#39;Ivoire" -> "Cote D'Ivoire")
    decoded = html.unescape(nationality)

    # 1. そのまま検索
    flag = NATIONALITY_FLAGS.get(decoded)
    if flag:
        return flag

    # 2. 空白をハイフンに置換して再試行 (API-Football 形式: "South Korea" -> "South-Korea")
    hyphenated = decoded.replace(" ", "-")
    flag = NATIONALITY_FLAGS.get(hyphenated)
    if flag:
        return flag

    # 3. ハイフンを空白に置換して再試行 ("Cote-D-Ivoire" -> "Cote D'Ivoire" などは難しいが一般的なものはカバー)
    spaced = decoded.replace("-", " ")
    flag = NATIONALITY_FLAGS.get(spaced)
    if flag:
        return flag

    # 4. 特定の有名なエイリアス対応
    aliases = {
        "Republic of Ireland": "Ireland",
        "DR Congo": "Congo DR",
        "North Macedonia": "Macedonia",
        "Bosnia and Herzegovina": "Bosnia",
    }
    alias_target = aliases.get(decoded)
    if alias_target:
        return NATIONALITY_FLAGS.get(alias_target, "")

    return ""


def format_player_with_flag(name: str, nationality: str) -> str:
    """
    選手名と国籍から「選手名 🇫🇷」形式の文字列を生成
    """
    flag = get_flag_emoji(nationality)
    if flag:
        return f"{name} {flag}"
    return name


def get_flagcdn_country_code(nationality: str) -> str:
    """
    国名から flagcdn 用の国コードを取得
    """
    if not nationality:
        return ""

    decoded = html.unescape(nationality)
    special_code = FLAGCDN_SPECIAL_CODES.get(decoded)
    if special_code:
        return special_code

    flag = get_flag_emoji(decoded)
    if len(flag) != 2:
        return ""

    first, second = (ord(ch) for ch in flag)
    if not (0x1F1E6 <= first <= 0x1F1FF and 0x1F1E6 <= second <= 0x1F1FF):
        return ""

    return f"{chr(first - 0x1F1E6 + ord('a'))}" f"{chr(second - 0x1F1E6 + ord('a'))}"
