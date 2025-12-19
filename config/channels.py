"""
YouTubeチャンネル設定

信頼できるチャンネルのハンドル名/IDを管理。
YouTube Data API v3でchannelId検索に使用する。

注意: ハンドル名(@xxx)はAPIで直接使用できないため、
初回アクセス時にチャンネルIDに解決してキャッシュする必要がある。
"""

# EPL チーム公式チャンネル
EPL_TEAM_CHANNELS = {
    "Manchester City": "@mancity",
    "Arsenal": "@Arsenal",
    "Chelsea": "@chelseafc",
    "Liverpool": "@LiverpoolFC",
    "Manchester United": "@manutd",
    "Tottenham": "@SpursOfficial",
    "Newcastle": "@NUFC",
    "Aston Villa": "@avaboringvillage",  # チャンネル要確認
    "Brighton": "@OfficialBHAFC",
    "Fulham": "@FulhamFC",
    "Nottingham Forest": "@NFFC",
    "Bournemouth": "@afcbournemouth",
}

# CL ビッグクラブ公式チャンネル
CL_TEAM_CHANNELS = {
    "Barcelona": "@fcbarcelona",
    "Real Madrid": "@realmadrid",
    "Bayern Munich": "@fcbayern",
    "Paris Saint Germain": "@PSGinside",
    "Inter": "@Inter",
    "AC Milan": "@acmilan",
    "Juventus": "@juventus",
    "Atletico Madrid": "@atleticodemadrid",
    "Borussia Dortmund": "@BVB",
}

# リーグ公式チャンネル
LEAGUE_CHANNELS = {
    "Premier League": "@premierleague",
    "UEFA Champions League": "@UEFA",
    "La Liga": "@LaLiga",
    "Serie A": "@SerieA",
    "Bundesliga": "@bundesliga",
}

# 放送局・メディアチャンネル
BROADCASTER_CHANNELS = {
    "Sky Sports Football": "@SkySportsFootball",
    "TNT Sports": "@tntsports",
    "DAZN Japan": "@DAZNJapan",
    "BBC Sport": "@BBCSport",
}

# 戦術分析チャンネル
TACTICS_CHANNELS = {
    "Tifo Football": "@TifoFootball_",
    "The Athletic FC": "@TheAthleticFC",
    "Leo the football TV": "@Leothefoot",  # 日本語
}


def get_team_channel(team_name: str) -> str | None:
    """チーム名からチャンネルハンドルを取得"""
    # EPLから探す
    if team_name in EPL_TEAM_CHANNELS:
        return EPL_TEAM_CHANNELS[team_name]
    # CLから探す
    if team_name in CL_TEAM_CHANNELS:
        return CL_TEAM_CHANNELS[team_name]
    return None


def get_all_channels() -> dict:
    """全チャンネルを統合して返す"""
    return {
        "teams": {**EPL_TEAM_CHANNELS, **CL_TEAM_CHANNELS},
        "leagues": LEAGUE_CHANNELS,
        "broadcasters": BROADCASTER_CHANNELS,
        "tactics": TACTICS_CHANNELS,
    }
