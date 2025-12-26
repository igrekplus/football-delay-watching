"""
YouTubeチャンネル設定

信頼できるチャンネルのハンドル名/IDを管理。
YouTube Data API v3でchannelId検索に使用する。

注意: ハンドル名(@xxx)はAPIで直接使用できないため、
初回アクセス時にチャンネルIDに解決してキャッシュする必要がある。
"""

from typing import Optional, Dict

# =============================================================================
# 信頼チャンネル（post-fetchフィルタ用）
# チャンネルID: {"name": 表示名, "handle": ハンドル, "category": カテゴリ}
# =============================================================================

TRUSTED_CHANNELS: Dict[str, Dict] = {
    # ====== チーム公式（EPL）======
    # 実際のチャンネルIDはログから取得
    "UCkzCjdRMrW2vXLx8mvPVLdQ": {"name": "Man City", "handle": "@mancity", "category": "team"},
    "UCBTy8j2cPy6zw68godcE7MQ": {"name": "Arsenal", "handle": "@Arsenal", "category": "team"},
    "UCpryVRk_VDudG8SHXgWcG0w": {"name": "Arsenal", "handle": "@arsenal", "category": "team"},
    "UCU2PacFf99vhb5boBUeckbQ": {"name": "Chelsea", "handle": "@chelseafc", "category": "team"},
    "UC9LQwHZoucFT94I2h6JOcjw": {"name": "Liverpool", "handle": "@LiverpoolFC", "category": "team"},
    "UC6yW44UGJJBvYTlfC7CRg2Q": {"name": "Manchester United", "handle": "@manutd", "category": "team"},
    "UCEg25rdRZXg32iwai6N6l0w": {"name": "Tottenham", "handle": "@SpursOfficial", "category": "team"},
    "UCWL2s9v6E6r0YMPSl9xZJnw": {"name": "Newcastle United", "handle": "@NUFC", "category": "team"},
    "UCSAJqSWicyatLAhOqMfjxRw": {"name": "Brighton", "handle": "@OfficialBHAFC", "category": "team"},
    "UC6QlrbRd_WmGPFZM3FebpkQ": {"name": "Fulham", "handle": "@FulhamFC", "category": "team"},
    "UChIWZA2-w04XdMRHPsYcvAw": {"name": "Nottingham Forest", "handle": "@NFFC", "category": "team"},
    "UChBePPmH51FJpJTNm8cDG2Q": {"name": "Bournemouth", "handle": "@afcbournemouth", "category": "team"},
    "UCCNOsmurvpEit9paBOzWtUg": {"name": "West Ham United", "handle": "@westhamunited", "category": "team"},
    
    # ====== チーム公式（CL/国際）======
    "UCHVWgs35DG0xHQkDFYl4xYg": {"name": "Barcelona", "handle": "@fcbarcelona", "category": "team"},
    "UCWV3obpZVGgJ3j9FVhEjF2Q": {"name": "Real Madrid", "handle": "@realmadrid", "category": "team"},
    "UCZVQIDzVnfbNPhSjsNqxowQ": {"name": "Bayern Munich", "handle": "@fcbayern", "category": "team"},
    "UCuJBU0o4b7VGJWJjc1LQe5A": {"name": "Inter", "handle": "@Inter", "category": "team"},
    "UCM0oAgW6Qa4AwlVg8hyl-eQ": {"name": "AC Milan", "handle": "@acmilan", "category": "team"},
    "UCeMBL8ByEKnFlF1dg18eCHg": {"name": "Juventus", "handle": "@juventus", "category": "team"},
    "UCS4HYos2BkL04TFykHZ5b2Q": {"name": "Atletico Madrid", "handle": "@atleticodemadrid", "category": "team"},
    "UCvDdWG1dMvjEDuHpr6aXzqQ": {"name": "Borussia Dortmund", "handle": "@BVB", "category": "team"},
    
    # ====== リーグ公式 ======
    "UCG5qGWdu8nIRZqJ_GgDwQ-w": {"name": "Premier League", "handle": "@premierleague", "category": "league"},
    "UCyGa1YEx9ST66rYrJTGIKOw": {"name": "UEFA", "handle": "@UEFA", "category": "league"},
    "UCM5gMM_HKvHNh7C__MBL9Xg": {"name": "La Liga", "handle": "@LaLiga", "category": "league"},
    "UCBJsMZfYefxFd2UNd6eLfKg": {"name": "Serie A", "handle": "@SerieA", "category": "league"},
    "UCeSPVgMlaC2DhmCT60G6_qQ": {"name": "Bundesliga", "handle": "@bundesliga", "category": "league"},
    
    # ====== 放送局・メディア ======
    "UCcw05gGzjLIs5dnxGkQHMvw": {"name": "Sky Sports News", "handle": "@SkySportsNews", "category": "broadcaster"},
    "UCEvWGu9_OFfIaC5Lz_i2dkg": {"name": "Sky Sports Football", "handle": "@SkySportsFootball", "category": "broadcaster"},
    "UCuIXf9o7jB34bPl8tXHYEGw": {"name": "TNT Sports", "handle": "@tntsports", "category": "broadcaster"},
    "UCSZ21xyG8w_33KriMM69IxQ": {"name": "DAZN Football", "handle": "@DAZNFootball", "category": "broadcaster"},
    "UCf3sCM5LyzU1hI_lU4Av3eQ": {"name": "DAZN Japan", "handle": "@DAZNJapan", "category": "broadcaster"},
    "UCoFLB_Gw_AoxUuuzKjXrc_Q": {"name": "DAZN Japan", "handle": "@daznjapan", "category": "broadcaster"},
    "UCFCxCBBybXz6mR8A6G3e3Lg": {"name": "BBC Sport", "handle": "@BBCSport", "category": "broadcaster"},
    "UCWw6scNyopJ0yjMu1SyOEyw": {"name": "talkSPORT", "handle": "@talkSPORT", "category": "broadcaster"},
    "UCMjvvElkdLRTgcTKklAUkSw": {"name": "U-NEXT フットボール", "handle": "@unext_football", "category": "broadcaster"},
    
    # ====== 戦術分析 ======
    "UCGYlBmk04IsNLTWbRgS-xkQ": {"name": "Tifo Football", "handle": "@TifoFootball_", "category": "tactics"},
    "UCp8IqNfaxeE8gy6SQsqbvHw": {"name": "The Athletic FC", "handle": "@TheAthleticFC", "category": "tactics"},
    "UC0N2Fv3QGMSR2R3aB-3rZTw": {"name": "レオザフットボール", "handle": "@Leothefoot", "category": "tactics"},
    "UCpZ8KoBzFcIJUzg4NL-H3Dw": {"name": "CRACK FOOTBALL", "handle": "@CRACKfootball", "category": "tactics"},
    "UCGWYb9tLAsmKXKIDKMBTbWw": {"name": "Football Made Simple", "handle": "@FootballMadeSimple", "category": "tactics"},
    "UCifwRb0DHe-NjHT1GahgWmA": {"name": "GOAT理論【切り抜き】", "handle": "@goat_theory", "category": "tactics"},
    "UCkWccBKBP0pvnUhuplw3lIA": {"name": "スポルティーバ", "handle": "@sportiva", "category": "media"},
    "UC8yHePe_RgUBE-waRWy6olw": {"name": "PIVOT 公式チャンネル", "handle": "@pivot00", "category": "media"},
    "UC5a1Zmq6dNNKKaW_sL6tjIA": {"name": "レオザマニア【Leothefootball】公認切り抜き", "handle": "@レオザマニア", "category": "tactics"},
}

# =============================================================================
# ハンドル名からチャンネルIDを逆引き
# =============================================================================
HANDLE_TO_ID = {info["handle"]: cid for cid, info in TRUSTED_CHANNELS.items()}


def is_trusted_channel(channel_id: str) -> bool:
    """チャンネルIDが信頼チャンネルかどうかを判定"""
    return channel_id in TRUSTED_CHANNELS


def get_channel_info(channel_id: str) -> Dict:
    """チャンネルIDからメタデータを取得"""
    return TRUSTED_CHANNELS.get(channel_id, {"name": "Unknown", "handle": "", "category": "unknown"})


def get_channel_display_name(channel_id: str, fallback_name: str = "Unknown") -> str:
    """チャンネルIDから表示名を取得（信頼チャンネルならその名前、そうでなければフォールバック）"""
    info = TRUSTED_CHANNELS.get(channel_id)
    if info:
        return info["name"]
    return fallback_name


# =============================================================================
# 後方互換性のための既存構造（将来的に削除予定）
# =============================================================================

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
    "West Ham United": "@westhamunited",
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
    "CRACK FOOTBALL": "@CRACKfootball",
    "Football Made Simple": "@FootballMadeSimple",
}


def get_team_channel(team_name: str) -> Optional[str]:
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
