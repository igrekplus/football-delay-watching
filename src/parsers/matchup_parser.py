import re
import logging
from typing import List
from dataclasses import dataclass
from html import escape

logger = logging.getLogger(__name__)

@dataclass
class PlayerMatchup:
    """選手マッチアップ情報"""
    header: str # "🇯🇵 日本" や "1. エース対決" など
    player1_name: str
    player1_team: str
    player2_name: str
    player2_team: str
    description: str

def parse_matchup_text(llm_output: str) -> List[PlayerMatchup]:
    """
    LLM出力から選手マッチアップ情報を抽出
    同国対決、キーマッチアップの両方に対応
    """
    if not llm_output:
        return []
        
    matchups = []
    
    # セクションを分割
    # キーマッチアップなどで "1. **選手** vs **選手**" のような形式もあるため
    # まずは見出し（国旗や数字）で分割を試みる
    # パターン1: 🇯🇵 **日本**
    # パターン2: 1. **選手** vs ...
    
    # セクション分割（2つ以上の改行、または箇条書きの開始）
    sections = [s.strip() for s in re.split(r'\n\s*(?=\d+\.|\n|[🇦-🇿🏴])', llm_output) if s.strip()]
    
    # ヘッダーパターン: 
    # 1. 🏴󠁧󠁢󠁳󠁣󠁴󠁿 **イングランド**
    # 2. **注目選手**
    # 3. 1.
    header_pattern = r'^([🇦-🇿🏴\U0001f1e6-\U0001f1ff\U000e0020-\U000e007f\d\.\s]+(?:\*\*.*?\*\*)?)'
    
    # 選手情報のパターン:
    # "**選手A**（チームA） vs **選手B**（チームB）" または "**選手A**（チームA）と**選手B**（チームB）"
    player_pattern = r'\*\*(.+?)\*\*[\(（](.+?)[\)）]\s*(?:vs|と)\s*\*\*(.+?)\*\*[\(（](.+?)[\)）]'
    
    for section in sections:
        # ヘッダー（国名や番号）の抽出
        header = ""
        header_match = re.match(header_pattern, section)
        if header_match:
            header = header_match.group(1).strip()
            content = section[header_match.end():].strip()
        else:
            content = section
            
        # 選手情報を抽出
        player_match = re.search(player_pattern, content)
        if not player_match:
            logger.debug(f"Player pattern not found in section: {section[:50]}...")
            continue
            
        # 説明文の抽出（選手情報の直後から最後まで）
        description_start = player_match.end()
        # 句点や改行で始まる場合はそれを取り除く
        description = re.sub(r'^[。．.\s]+', '', content[description_start:]).strip()
        
        matchup = PlayerMatchup(
            header=escape(header),
            player1_name=escape(player_match.group(1).strip()),
            player1_team=escape(player_match.group(2).strip()),
            player2_name=escape(player_match.group(3).strip()),
            player2_team=escape(player_match.group(4).strip()),
            description=escape(description)
        )
        
        matchups.append(matchup)
    
    return matchups
