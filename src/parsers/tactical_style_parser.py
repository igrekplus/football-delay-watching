"""戦術スタイルセクションのテキストパーサー"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TacticalStyle:
    """チーム別の戦術スタイル情報"""

    team: str
    description: str


def parse_tactical_style_text(
    text: str, home_team: str, away_team: str
) -> list[TacticalStyle]:
    """
    戦術スタイルのテキストを解析してチーム別のリストを返す

    Expected format 1 (Structured):
    #### {team_name}
    - description...

    Expected format 2 (Unstructured):
    {team_name}は、...
    """
    logger.debug(f"Parsing tactical style text (length: {len(text)})")

    # セクションの抽出
    content = text
    if "### 🎯 戦術スタイル" in text:
        content = text.split("### 🎯 戦術スタイル")[-1]

    # 次のセクション（### ）までを対象とする
    next_section = re.search(r"\n### ", content)
    if next_section:
        content = content[: next_section.start()]

    content = content.strip()
    results = []

    # ヘルパー: チーム名マッチング
    def _match_team(name):
        n = name.strip().lower()
        if n in home_team.lower() or home_team.lower() in n:
            return home_team
        if n in away_team.lower() or away_team.lower() in n:
            return away_team
        return None

    # 1. 構造化された分割（#### ）を試みる
    if re.search(r"(?m)^####\s*", content):
        logger.debug("Structured headers (####) found.")
        parts = re.split(r"(?m)^####\s*", content)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lines = part.split("\n")
            team_header = lines[0].strip()
            target_team = _match_team(team_header)

            if target_team:
                desc = "\n".join(lines[1:]).strip()
                if desc and not any(r.team == target_team for r in results):
                    results.append(TacticalStyle(team=target_team, description=desc))
                    logger.debug(f"Parsed via header: {target_team}")

    # 2. 段落ベースのパース（構造化で見つからなかったチームを補完）
    if len(results) < 2:
        logger.debug(
            f"Attempting paragraph-based parsing for remaining teams. Current results: {[r.team for r in results]}"
        )
        found_teams = [r.team for r in results]

        # 段落（空行区切り）で分割
        paragraphs = re.split(r"\n\s*\n", content)
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para or para.startswith("####"):
                continue

            # 段落の先頭にチーム名があるかチェック
            matched_team = None
            if para.lower().startswith(home_team.lower()):
                matched_team = home_team
            elif para.lower().startswith(away_team.lower()):
                matched_team = away_team

            if matched_team and matched_team not in found_teams:
                # チーム名を除いた残りを説明文とする
                desc = para[len(matched_team) :].strip()
                # 先頭の助詞や記号を除去
                desc = re.sub(r"^[はの、:\s-]+", "", desc)
                if desc:
                    results.append(TacticalStyle(team=matched_team, description=desc))
                    found_teams.append(matched_team)
                    logger.debug(f"Parsed via paragraph {i}: {matched_team}")

    logger.info(f"Parsed {len(results)} tactical styles: {[r.team for r in results]}")
    return results
