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
            f"Attempting robust line-based parsing for remaining teams. Current results: {[r.team for r in results]}"
        )
        found_teams = [r.team for r in results]

        # 行単位で処理して、チーム名の出現を柔軟に検知
        lines = content.split("\n")
        current_team = None
        current_desc = []

        for line in lines:
            line_orig = line
            line = line.strip()
            if not line:
                continue

            # 新しいチームの開始をチェック
            matched_team = None
            for team in [home_team, away_team]:
                if team in found_teams:
                    continue

                # チーム名が最初の方に含まれているかチェック
                # 記号 (**, #, :) などを考慮して、最初の50文字以内を探索
                line_head = line[:50].lower()
                team_lower = team.lower()

                if team_lower in line_head:
                    start_pos = line_head.find(team_lower)
                    # チーム名の前が記号のみかチェック（誤検知防止）
                    prefix = line_head[:start_pos]
                    if re.match(r"^[ :\*\-#>]*$", prefix):
                        matched_team = team
                        break

            if matched_team:
                # 前のチームがあれば保存
                if current_team and current_desc:
                    results.append(
                        TacticalStyle(
                            team=current_team,
                            description="\n".join(current_desc).strip(),
                        )
                    )
                    found_teams.append(current_team)

                current_team = matched_team
                # チーム名と、その周りの記号類を除去して説明文の開始部分を取得
                # チーム名までの記号 + チーム名 + 直後の記号（コロン、太字閉じ、助詞等）を除去
                pattern = f"^[ :\\*\\-#>]*{re.escape(current_team)}[ :\\*はの、\\s-]*"
                desc_start = re.sub(pattern, "", line, flags=re.IGNORECASE)
                current_desc = [desc_start] if desc_start else []
            elif current_team:
                current_desc.append(line_orig)

        # 最後のチームを保存
        if current_team and current_desc:
            if not any(r.team == current_team for r in results):
                results.append(
                    TacticalStyle(
                        team=current_team, description="\n".join(current_desc).strip()
                    )
                )

    # 後処理: description のクリーンアップ
    for r in results:
        # 先頭の不要な記号を再度除去
        r.description = re.sub(r"^[ :\*\-#>はの、\s-]+", "", r.description).strip()

    logger.info(f"Parsed {len(results)} tactical styles: {[r.team for r in results]}")
    return results
