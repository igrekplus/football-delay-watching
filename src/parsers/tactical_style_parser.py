"""戦術スタイルセクションのテキストパーサー"""
import re
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

@dataclass
class TacticalStyle:
    """チーム別の戦術スタイル情報"""
    team: str
    description: str

def parse_tactical_style_text(text: str, home_team: str, away_team: str) -> List[TacticalStyle]:
    """
    戦術スタイルのテキストを解析してチーム別のリストを返す
    
    Expected format:
    ### 🎯 戦術スタイル
    #### Team Name
    - Description...
    """
    results = []
    
    # セクションの抽出
    separator = "### 🎯 戦術スタイル"
    if separator in text:
        parts = text.split(separator)
        if len(parts) > 1:
            content = parts[1]
            # 次のセクション（### ）までを対象とする
            next_section = re.search(r'\n### ', content)
            if next_section:
                content = content[:next_section.start()]
        else:
            return []
    else:
        content = text
        
    # チーム名（#### ）で分割
    team_parts = re.split(r'\n####\s*', content)
    
    for part in team_parts:
        if not part.strip():
            continue
            
        lines = part.strip().split('\n')
        team_name = lines[0].strip()
        description = '\n'.join(lines[1:]).strip()
        
        # チーム名が home_team または away_team に含まれるかチェック（あいまい一致対応）
        target_team = None
        if team_name.lower() in home_team.lower() or home_team.lower() in team_name.lower():
            target_team = home_team
        elif team_name.lower() in away_team.lower() or away_team.lower() in team_name.lower():
            target_team = away_team
            
        if target_team and description:
            results.append(TacticalStyle(team=target_team, description=description))
            
    # 何も取得できなかった場合は、段落ごとに分割してチーム名を探す（後方互換性）
    if not results:
        logger.debug("No structured tactical styles found, attempting paragraph-based parsing")
        
        # 段落（空行区切り）で分割
        paragraphs = re.split(r'\n\s*\n', content.strip())
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 段落の先頭にチーム名があるかチェック
            matched_team = None
            if para.lower().startswith(home_team.lower()):
                matched_team = home_team
            elif para.lower().startswith(away_team.lower()):
                matched_team = away_team
            
            if matched_team:
                # チーム名を除いた残りを説明文とする
                desc = para[len(matched_team):].strip()
                # 先頭の「は、」「:」などを除去
                desc = re.sub(r'^[はの、:\s]+', '', desc)
                if desc and not any(r.team == matched_team for r in results):
                    results.append(TacticalStyle(team=matched_team, description=desc))
                
    logger.info(f"Parsed {len(results)} tactical styles")
    return results
