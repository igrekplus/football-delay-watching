"""同国対決・キーマッチアップのLLM出力をパースする"""
import re
from typing import List
from dataclasses import dataclass

@dataclass
class PlayerMatchup:
    """選手マッチアップ情報"""
    country: str
    country_flag: str
    player1_name: str
    player1_team: str
    player2_name: str
    player2_team: str
    description: str

def parse_matchup_text(llm_output: str) -> List[PlayerMatchup]:
    """
    LLM出力から選手マッチアップ情報を抽出
    
    Args:
        llm_output: LLMが生成したマッチアップテキスト
        
    Returns:
        PlayerMatchup のリスト
    """
    if not llm_output:
        return []
        
    matchups = []
    
    # セクションを分割
    # 空行で分割し、非表示の改行文字なども考慮
    sections = [s.strip() for s in re.split(r'\n\s*\n', llm_output) if s.strip()]
    
    # 国情報のパターン: "🇯🇵 **日本**" または "🏴󠁧󠁢󠁥󠁮󠁧󠁿 **イングランド**"
    country_pattern = r'([🇦-🇿🏴\U0001f1e6-\U0001f1ff]+)\s*\*\*(.+?)\*\*'
    
    # 選手情報のパターン:
    # "**選手A**（チームA）と**選手B**（チームB）。[説明]"
    # 全角・半角の括弧の両方に対応
    player_pattern = r'\*\*(.+?)\*\*[\(（](.+?)[\)）].*?と.*?\*\*(.+?)\*\*[\(（](.+?)[\)）][。．.](.+)'
    
    for section in sections:
        # 国情報を抽出
        country_match = re.search(country_pattern, section)
        if not country_match:
            continue
            
        country_flag = country_match.group(1)
        country_name = country_match.group(2)
        
        # 国情報の行を除去して、残りの部分から選手情報を探す
        content_after_country = re.sub(country_pattern, "", section, count=1).strip()
        
        # 選手情報を抽出
        player_match = re.search(player_pattern, content_after_country, re.DOTALL)
        if not player_match:
            continue
            
        matchup = PlayerMatchup(
            country=country_name,
            country_flag=country_flag,
            player1_name=player_match.group(1).strip(),
            player1_team=player_match.group(2).strip(),
            player2_name=player_match.group(3).strip(),
            player2_team=player_match.group(4).strip(),
            description=player_match.group(5).strip()
        )
        
        matchups.append(matchup)
    
    return matchups
