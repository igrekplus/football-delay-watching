from dataclasses import dataclass
from typing import List, Optional
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class KeyPlayer:
    """キープレイヤー情報"""
    name: str
    team: str
    description: str
    detailed_description: Optional[str] = None

def parse_key_player_text(text: str) -> List[KeyPlayer]:
    """
    LLM出力のキープレイヤーセクションをパースする
    
    形式例:
    **Bukayo Saka** (Arsenal): サマリテキスト...
    **詳細**
    詳細テキスト...
    """
    if not text:
        return []
        
    key_players = []
    
    # 選手ごとのチャンクに分割する簡易ロジック
    # 行頭が `**Name** (Team)` で始まるものを基準にする
    
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    current_player = None
    buffer = []
    
    for line in lines:
        # 新しい選手の開始判定
        match = re.match(r'\*\*([^*]+)\*\*\s*\(([^)]+)\)[:\s-](.+)', line)
        if match:
            # 前の選手を保存
            if current_player:
                full_desc = "\n".join(buffer)
                _finalize_player(current_player, full_desc, key_players)
            
            # 新しい選手を開始
            current_player = {
                "name": match.group(1).strip(),
                "team": match.group(2).strip()
            }
            buffer = [match.group(3).strip()]
        else:
            # 継続行としてバッファに追加
            if current_player:
                buffer.append(line)
    
    # 最後の選手を保存
    if current_player:
        full_desc = "\n".join(buffer)
        _finalize_player(current_player, full_desc, key_players)
            
    logger.info(f"Parsed {len(key_players)} key players")
    return key_players

def _finalize_player(player_dict, full_desc, players_list):
    """説明文をサマリと詳細に分割してリストに追加"""
    summary = full_desc
    detail = None
    
    # "詳細" キーワードで分割
    # パターン: "**詳細**", "**詳細:**", "【詳細】" など
    split_match = re.search(r'(\*\*詳細\*\*|【詳細】|詳細:)', full_desc)
    
    if split_match:
        summary = full_desc[:split_match.start()].strip()
        detail = full_desc[split_match.end():].strip()
        # 先頭のコロンや改行を除去
        detail = re.sub(r'^[:\s]+', '', detail)
    
    players_list.append(KeyPlayer(
        name=player_dict["name"],
        team=player_dict["team"],
        description=summary,
        detailed_description=detail
    ))
