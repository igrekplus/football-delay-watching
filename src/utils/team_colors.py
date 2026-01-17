"""
Team Color Mappings
Used for dynamic match report styling (pitch markings, player cards).
Colors are chosen to be visible on dark backgrounds.
"""

TEAM_COLORS = {
    # Premier League
    "Arsenal": "#EF0107",
    "Aston Villa": "#95BBE5",  # Claret is too dark? Use Blue
    "Bournemouth": "#DA291C",
    "Brentford": "#E30613",
    "Brighton": "#0057B8",
    "Chelsea": "#034694",
    "Crystal Palace": "#1B458F",
    "Everton": "#003399",
    "Fulham": "#CC0000",  # White kit but red accents? Or just white.
    "Liverpool": "#C8102E",
    "Luton Town": "#F78F1E",
    "Manchester City": "#6CABDD",
    "Man City": "#6CABDD",
    "Manchester United": "#DA291C",
    "Man United": "#DA291C",
    "Newcastle United": "#FFFFFF",  # Black/White. Use White for dark bg.
    "Newcastle": "#FFFFFF",
    "Nottingham Forest": "#DD0000",
    "Sheffield United": "#EE2737",
    "Tottenham Hotspur": "#FFFFFF",  # Use White for Navy kit vs Dark BG
    "Tottenham": "#FFFFFF",
    "West Ham United": "#7A263A",
    "West Ham": "#7A263A",
    "Wolverhampton Wanderers": "#FDB913",
    "Wolves": "#FDB913",
    # La Liga
    "Alaves": "#009AD7",
    "Almeria": "#ED1C24",
    "Athletic Club": "#EE2523",
    "Atletico Madrid": "#CB3524",
    "Barcelona": "#EDBB00",  # Use Gold/Yellow for visibility? Or the Blue? Blue #004D98 might be low contrast.
    # Let's use standard Blaugrana Red/Blue but ensure brightness.
    "FC Barcelona": "#DB0030",
    "Betis": "#009B45",
    "Cadiz": "#F3D500",
    "Celta Vigo": "#AFCBFF",
    "Getafe": "#0059CF",
    "Girona": "#EF3340",
    "Granada": "#A61B2B",
    "Las Palmas": "#F4C300",
    "Mallorca": "#E20613",
    "Osasuna": "#0A346F",
    "Rayo Vallecano": "#FFFFFF",
    "Real Madrid": "#FFFFFF",  # White
    "Real Sociedad": "#0067B1",
    "Sevilla": "#FFFFFF",
    "Valencia": "#FFFFFF",
    "Villarreal": "#FBE100",
    # Serie A
    "AC Milan": "#FB090B",
    "Atalanta": "#1E71B8",
    "Bologna": "#1A2F48",
    "Cagliari": "#002350",
    "Empoli": "#00579C",
    "Fiorentina": "#482E92",
    "Frosinone": "#FFD500",
    "Genoa": "#BA002D",
    "Inter": "#008FD7",  # Use vivid blue
    "Juventus": "#FFFFFF",
    "Lazio": "#87D8F7",
    "Lecce": "#DC202D",
    "Monza": "#E30F19",
    "Napoli": "#12A0D7",
    "Roma": "#F0BC42",  # Yellow/Orange for visibility
    "Salernitana": "#8A1E41",
    "Sassuolo": "#00A752",
    "Torino": "#8A1E41",
    "Udinese": "#FFFFFF",
    "Verona": "#005395",
    # Bundesliga
    "Augsburg": "#BA3733",
    "Bayern Munich": "#DC052D",
    "Bochum": "#005CA9",
    "Bremen": "#1D9053",
    "Darmstadt": "#004E8A",
    "Dortmund": "#FDE100",
    "Frankfurt": "#E1000F",
    "Freiburg": "#000000",  # On dark bg? Bad. Use White.
    "SC Freiburg": "#FFFFFF",
    "Heidenheim": "#E2001A",
    "Hoffenheim": "#005CA9",
    "Koln": "#ED1C24",
    "Leipzig": "#E41F32",  # RB Leipzig
    "Leverkusen": "#E32221",
    "Mainz": "#C3141E",
    "Gladbach": "#FFFFFF",  # Bor. Moenchengladbach
    "Stuttgart": "#E32219",
    "Union Berlin": "#D4011D",
    "Wolfsburg": "#65B32E",
    # Defaults
    "Default Home": "#3a6ea5",
    "Default Away": "#e74c3c",
}


def get_team_color(team_name: str, default: str = "#CCCCCC") -> str:
    """Get color for team name, lenient match"""
    # Exact match
    if team_name in TEAM_COLORS:
        return TEAM_COLORS[team_name]

    # Check partials or variations if needed (simple for now)
    return default
