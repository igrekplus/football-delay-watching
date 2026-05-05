"""
代表戦選手カードで使用するクラブ名略称マッピング。
API-Football が返すフルネームをキーに、カード表示用の短縮名を値に持つ。
掲載国の代表戦で主に登場するクラブに限定して管理する。
"""

CLUB_ABBREVIATIONS: dict[str, str] = {
    # England
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Tottenham Hotspur": "Tottenham",
    "Newcastle United": "Newcastle",
    "West Ham United": "West Ham",
    "Nottingham Forest": "Nott'm Forest",
    "Leicester City": "Leicester",
    "Brighton & Hove Albion": "Brighton",
    "Wolverhampton Wanderers": "Wolves",
    "Sheffield United": "Sheffield Utd",
    # Spain
    "Atlético Madrid": "Atlético",
    "Athletic Club": "Athletic Bilbao",
    "Real Sociedad": "Sociedad",
    "Real Betis": "Betis",
    "Deportivo Alavés": "Alavés",
    "Rayo Vallecano": "Rayo",
    # Germany
    "Borussia Dortmund": "Dortmund",
    "Bayer Leverkusen": "Leverkusen",
    "Bayern München": "Bayern",
    "Eintracht Frankfurt": "Frankfurt",
    "Borussia Mönchengladbach": "M'gladbach",
    "RB Leipzig": "Leipzig",
    "SC Freiburg": "Freiburg",
    # France
    "Paris Saint-Germain": "PSG",
    "Olympique Lyonnais": "Lyon",
    "Olympique de Marseille": "Marseille",
    "Stade Rennais FC": "Rennes",
    "AS Monaco": "Monaco",
    "LOSC Lille": "Lille",
    # Italy
    "Inter Milan": "Inter",
    "AC Milan": "Milan",
    "Juventus": "Juventus",
    "SS Lazio": "Lazio",
    "AS Roma": "Roma",
    "Atalanta BC": "Atalanta",
    "SSC Napoli": "Napoli",
    "ACF Fiorentina": "Fiorentina",
    "Torino FC": "Torino",
    # Netherlands
    "AFC Ajax": "Ajax",
    # Portugal
    "Sporting CP": "Sporting",
    "SL Benfica": "Benfica",
    "FC Porto": "Porto",
    # Turkey
    "Galatasaray SK": "Galatasaray",
    "Fenerbahçe SK": "Fenerbahçe",
    "Beşiktaş JK": "Beşiktaş",
    # Saudi Arabia
    "Al Nassr": "Al Nassr",
    "Al-Ahli Saudi FC": "Al-Ahli",
    "Al-Ittihad Club": "Al-Ittihad",
    "Al Hilal Saudi FC": "Al Hilal",
}


def get_club_display_name(full_name: str) -> str:
    """略称マッピングを適用。未登録なら全名をそのまま返す。"""
    return CLUB_ABBREVIATIONS.get(full_name, full_name)
