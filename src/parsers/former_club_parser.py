import re
import logging
from typing import List
from dataclasses import dataclass
from html import escape

logger = logging.getLogger(__name__)

@dataclass
class FormerClubEntry:
    """古巣対決エントリ（1選手単位）"""
    name: str # 選手名
    team: str # 現所属チーム名
    description: str # 詳細・エピソード

def parse_former_club_text(llm_output: str) -> List[FormerClubEntry]:
    """
    LLM出力から古巣対決情報を抽出
    フォーマット:
    **選手名** (チーム名)
    説明文...
    """
    if not llm_output:
        return []
        
    entries = []
    
    # 選手名(チーム名) のパターン
    # **Name** (Team) 形式
    player_team_pattern = r'\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]'
    
    # パターンにマッチする箇所と、その間のテキストを抽出
    matches = list(re.finditer(player_team_pattern, llm_output))
    
    for i, match in enumerate(matches):
        name = match.group(1).strip()
        team = match.group(2).strip()
        
        # 説明文の開始位置
        desc_start = match.end()
        # 次のマッチがあればそこまで、なければ最後まで
        if i + 1 < len(matches):
            desc_end = matches[i+1].start()
        else:
            desc_end = len(llm_output)
            
        description = llm_output[desc_start:desc_end].strip()
        # 不要な記号や空行を除去
        description = re.sub(r'^[。．.\s\(\(（]+', '', description).strip()
        # Markdownの太字装飾を削除（description内）
        description = description.replace('**', '')
        
        entries.append(FormerClubEntry(
            name=escape(name),
            team=escape(team),
            description=escape(description)
        ))
    
    logger.info(f"Parsed {len(entries)} former club entries from LLM output")
    return entries
