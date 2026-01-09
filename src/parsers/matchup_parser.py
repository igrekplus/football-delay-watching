import re
import logging
from typing import List, Optional
from dataclasses import dataclass
from html import escape

logger = logging.getLogger(__name__)

@dataclass
class PlayerMatchup:
    """選手マッチアップ情報"""
    header: str # "🇯🇵 Japan" や "1." など
    player1_name: str
    player1_team: str
    player2_name: str
    player2_team: str
    description: str

def _extract_players(text: str) -> List[tuple]:
    """
    テキストから選手名とチーム名を抽出
    形式: **選手名** (チーム名) または **選手名**（チーム名）
    """
    # ボールド選手名 + 括弧チーム名のパターン（全角/半角両対応）
    pattern = r'\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]'
    return re.findall(pattern, text)

def parse_matchup_text(llm_output: str) -> List[PlayerMatchup]:
    """
    LLM出力から選手マッチアップ情報を抽出
    同国対決、キーマッチアップの両方に対応（柔軟なフォーマット対応）
    """
    if not llm_output:
        return []
        
    matchups = []
    
    # 1. まず行単位で処理（1行に1マッチアップの場合）
    # ヘッダー行（国旗 + 国名）の検出
    header_line_pattern = r'^([🇦-🇿🏴\U0001f1e6-\U0001f1ff\U000e0020-\U000e007f]+)\s*\*\*([^*]+)\*\*'
    
    lines = llm_output.split('\n')
    current_header = ""
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # ヘッダー行のチェック（国旗 + 国名）
        header_match = re.match(header_line_pattern, line)
        if header_match:
            # 前のセクションを処理
            if current_content:
                result = _process_section(current_header, '\n'.join(current_content))
                if result:
                    matchups.append(result)
            
            current_header = f"{header_match.group(1)} **{header_match.group(2)}**"
            # 同じ行に選手情報がある場合
            remaining = line[header_match.end():].strip()
            current_content = [remaining] if remaining else []
        else:
            current_content.append(line)
    
    # 最後のセクションを処理
    if current_content:
        result = _process_section(current_header, '\n'.join(current_content))
        if result:
            matchups.append(result)
    
    # 2. もしマッチアップが見つからなかった場合、vsパターンで直接検索
    if not matchups:
        vs_pattern = r'\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]\s*(?:vs|と)\s*\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]'
        for match in re.finditer(vs_pattern, llm_output):
            # 説明文は選手情報の後ろのテキスト
            desc_start = match.end()
            desc_end = llm_output.find('\n', desc_start)
            if desc_end == -1:
                desc_end = len(llm_output)
            description = re.sub(r'^[。．.\s]+', '', llm_output[desc_start:desc_end]).strip()
            
            matchups.append(PlayerMatchup(
                header="",
                player1_name=escape(match.group(1).strip()),
                player1_team=escape(match.group(2).strip()),
                player2_name=escape(match.group(3).strip()),
                player2_team=escape(match.group(4).strip()),
                description=escape(description)
            ))
    
    logger.info(f"Parsed {len(matchups)} matchups from LLM output")
    return matchups

def _process_section(header: str, content: str) -> Optional[PlayerMatchup]:
    """セクション（ヘッダー + コンテンツ）から1つのマッチアップを抽出"""
    players = _extract_players(content)
    
    if len(players) < 2:
        logger.debug(f"Less than 2 players found in section: {content[:50]}...")
        return None
    
    # 最初の2選手をペアとして扱う
    player1_name, player1_team = players[0]
    player2_name, player2_team = players[1]
    
    # 説明文: 2番目の選手情報以降のテキスト
    # 選手情報パターンを全て除去した残りのテキストを取得
    description = content
    for name, team in players[:2]:
        pattern = rf'\*\*{re.escape(name)}\*\*\s*[（\(]{re.escape(team)}[）\)]'
        description = re.sub(pattern, '', description)
    
    # 「は」「と」「の」などの接続詞と重複改行を整理
    description = re.sub(r'^\s*(?:は[、,]?\s*|と\s*|の\s*)', '', description)
    description = re.sub(r'^[。．.,、\s]+', '', description).strip()
    
    return PlayerMatchup(
        header=escape(header) if header else "",
        player1_name=escape(player1_name.strip()),
        player1_team=escape(player1_team.strip()),
        player2_name=escape(player2_name.strip()),
        player2_team=escape(player2_team.strip()),
        description=escape(description)
    )

