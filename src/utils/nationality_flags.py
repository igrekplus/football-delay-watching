import html
import re
import unicodedata

"""
国名から国旗絵文字へのマッピング辞書
API-Football が返す国名に対応
"""


def _normalize_lookup_key(value: str) -> str:
    """表記揺れ吸収用の比較キーを返す。"""
    decoded = html.unescape(value or "").strip()
    if not decoded:
        return ""

    normalized = unicodedata.normalize("NFKD", decoded)
    without_marks = "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    ).casefold()
    without_marks = without_marks.replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", without_marks)


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
    "Czechia": "🇨🇿",
    "Czech Republic": "🇨🇿",
    "Greece": "🇬🇷",
    "Turkey": "🇹🇷",
    "Russia": "🇷🇺",
    "Russian Federation": "🇷🇺",
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
    "Moldova, Republic of": "🇲🇩",
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
    "Monaco": "🇲🇨",
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
    "United States of America": "🇺🇸",
    "United Kingdom": "🇬🇧",
    "Great Britain": "🇬🇧",
    "Mexico": "🇲🇽",
    "Canada": "🇨🇦",
    "Bahamas": "🇧🇸",
    "Aruba": "🇦🇼",
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
    "Curaçao": "🇨🇼",
    "Cuba": "🇨🇺",
    "Dominican Republic": "🇩🇴",
    "Dominica": "🇩🇲",
    "Grenada": "🇬🇩",
    "Barbados": "🇧🇧",
    "Saint Kitts and Nevis": "🇰🇳",
    "Saint Lucia": "🇱🇨",
    "Saint Vincent and the Grenadines": "🇻🇨",
    "Antigua and Barbuda": "🇦🇬",
    "Bermuda": "🇧🇲",
    "Belize": "🇧🇿",
    "Puerto Rico": "🇵🇷",
    "Cayman Islands": "🇰🇾",
    "British Virgin Islands": "🇻🇬",
    "US Virgin Islands": "🇻🇮",
    "Turks and Caicos Islands": "🇹🇨",
    "Anguilla": "🇦🇮",
    "Montserrat": "🇲🇸",
    "Sint Maarten": "🇸🇽",
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
    "Cape Verde Islands": "🇨🇻",
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
    "South Sudan": "🇸🇸",
    "Libya": "🇱🇾",
    "Comoros": "🇰🇲",
    "Central African Republic": "🇨🇫",
    "Burundi": "🇧🇮",
    "Ethiopia": "🇪🇹",
    "Rwanda": "🇷🇼",
    "Malawi": "🇲🇼",
    "Botswana": "🇧🇼",
    "Chad": "🇹🇩",
    "Djibouti": "🇩🇯",
    "Eritrea": "🇪🇷",
    "Lesotho": "🇱🇸",
    "Mauritius": "🇲🇺",
    "Niger": "🇳🇪",
    "Seychelles": "🇸🇨",
    "Somalia": "🇸🇴",
    # アジア・オセアニア
    "Afghanistan": "🇦🇫",
    "Japan": "🇯🇵",
    "Korea Republic": "🇰🇷",
    "Korea, Republic of": "🇰🇷",
    "South Korea": "🇰🇷",
    "Korea, Democratic People's Republic of": "🇰🇵",
    "China": "🇨🇳",
    "Macao": "🇲🇴",
    "Macau": "🇲🇴",
    "Australia": "🇦🇺",
    "New Zealand": "🇳🇿",
    "Papua New Guinea": "🇵🇬",
    "Fiji": "🇫🇯",
    "Solomon Islands": "🇸🇧",
    "Vanuatu": "🇻🇺",
    "Samoa": "🇼🇸",
    "American Samoa": "🇦🇸",
    "Tonga": "🇹🇴",
    "Guam": "🇬🇺",
    "Northern Mariana Islands": "🇲🇵",
    "Cook Islands": "🇨🇰",
    "Tahiti": "🇵🇫",
    "Iran": "🇮🇷",
    "Iran, Islamic Republic of": "🇮🇷",
    "Saudi Arabia": "🇸🇦",
    "Qatar": "🇶🇦",
    "UAE": "🇦🇪",
    "United Arab Emirates": "🇦🇪",
    "Iraq": "🇮🇶",
    "Bangladesh": "🇧🇩",
    "Cambodia": "🇰🇭",
    "Nepal": "🇳🇵",
    "Pakistan": "🇵🇰",
    "Sri Lanka": "🇱🇰",
    "Maldives": "🇲🇻",
    "Mongolia": "🇲🇳",
    "Uzbekistan": "🇺🇿",
    "Thailand": "🇹🇭",
    "Vietnam": "🇻🇳",
    "Indonesia": "🇮🇩",
    "Malaysia": "🇲🇾",
    "Philippines": "🇵🇭",
    "Jordan": "🇯🇴",
    "Oman": "🇴🇲",
    "Bahrain": "🇧🇭",
    "Brunei": "🇧🇳",
    "Brunei Darussalam": "🇧🇳",
    "Laos": "🇱🇦",
    "Myanmar": "🇲🇲",
    "Singapore": "🇸🇬",
    "Syria": "🇸🇾",
    "Syrian Arab Republic": "🇸🇾",
    "Lebanon": "🇱🇧",
    "Palestine": "🇵🇸",
    "State of Palestine": "🇵🇸",
    "Kuwait": "🇰🇼",
    "India": "🇮🇳",
    "Kyrgyzstan": "🇰🇬",
    "Tajikistan": "🇹🇯",
    "Turkmenistan": "🇹🇲",
    "North Korea": "🇰🇵",
    "Eswatini": "🇸🇿",
    "Sao Tome and Principe": "🇸🇹",
    "Timor-Leste": "🇹🇱",
    "Timor Leste": "🇹🇱",
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

NORMALIZED_NATIONALITY_FLAGS = {
    _normalize_lookup_key(country): flag for country, flag in NATIONALITY_FLAGS.items()
}

NORMALIZED_NATIONALITY_ALIASES = {
    "republicofireland": "Ireland",
    "korearepublic": "South Korea",
    "korearepublicof": "South Korea",
    "republicofkorea": "South Korea",
    "iranislamicrepublicof": "Iran",
    "moldovarepublicof": "Moldova",
    "tanzaniaunitedrepublicof": "Tanzania",
    "russianfederation": "Russia",
    "syrianarabrepublic": "Syria",
    "boliviaplurinationalstateof": "Bolivia",
    "venezuelabolivarianrepublicof": "Venezuela",
    "unitedstatesofamerica": "United States",
    "thegambia": "Gambia",
    "caboverde": "Cape Verde",
    "capeverdeislands": "Cape Verde",
    "bruneidarussalam": "Brunei",
    "democraticpeoplesrepublicofkorea": "North Korea",
    "timorleste": "Timor-Leste",
    "palestinestateof": "Palestine",
    "palestinianterritories": "Palestine",
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

    # 2. クォート差や空白差を吸収して再試行
    normalized_quotes = (
        decoded.replace("’", "'").replace("`", "'").replace("´", "'").strip()
    )
    if normalized_quotes != decoded:
        flag = NATIONALITY_FLAGS.get(normalized_quotes)
        if flag:
            return flag

    # 3. 空白をハイフンに置換して再試行 (API-Football 形式: "South Korea" -> "South-Korea")
    hyphenated = normalized_quotes.replace(" ", "-")
    flag = NATIONALITY_FLAGS.get(hyphenated)
    if flag:
        return flag

    # 4. ハイフンを空白に置換して再試行
    spaced = normalized_quotes.replace("-", " ")
    flag = NATIONALITY_FLAGS.get(spaced)
    if flag:
        return flag

    # 5. 正規化して既知の国名・別名へ寄せる
    normalized_key = _normalize_lookup_key(normalized_quotes)
    flag = NORMALIZED_NATIONALITY_FLAGS.get(normalized_key)
    if flag:
        return flag

    alias_target = NORMALIZED_NATIONALITY_ALIASES.get(normalized_key)
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
