import logging
import re
from dataclasses import dataclass
from html import escape

logger = logging.getLogger(__name__)


@dataclass
class FormerClubEntry:
    """古巣対決エントリ（1選手単位）"""

    name: str  # 選手名
    team: str  # 現所属チーム名
    description: str  # 詳細・エピソード


def parse_former_club_text(
    llm_output: str, home_team: str = None, away_team: str = None
) -> list[FormerClubEntry]:
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
    player_team_pattern = r"\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]"

    # パターンにマッチする箇所と、その間のテキストを抽出
    matches = list(re.finditer(player_team_pattern, llm_output))

    # フィルタリング用のキーワード（チーム名の略称など）
    team_keywords = []

    from src.utils.team_name_translator import TeamNameTranslator

    translator = TeamNameTranslator()

    if home_team:
        team_keywords.extend(translator.get_katakana_keywords(home_team))
        team_keywords.append(home_team.lower())
        team_keywords.extend(
            [part.lower() for part in home_team.split() if len(part) > 3]
        )

    if away_team:
        team_keywords.extend(translator.get_katakana_keywords(away_team))
        team_keywords.append(away_team.lower())
        team_keywords.extend(
            [part.lower() for part in away_team.split() if len(part) > 3]
        )

    def is_relevant(desc: str) -> bool:
        if not team_keywords:
            return True  # キーワード指定がなければフィルタしない

        desc_lower = desc.lower()
        # 英語名またはカタカナキーワードのいずれかが含まれていればOK
        return any(kw.lower() in desc_lower for kw in team_keywords)

    for i, match in enumerate(matches):
        name = match.group(1).strip()
        team = match.group(2).strip()

        # 説明文の開始位置
        desc_start = match.end()
        # 次のマッチがあればそこまで、なければ最後まで
        if i + 1 < len(matches):
            desc_end = matches[i + 1].start()
        else:
            desc_end = len(llm_output)

        description = llm_output[desc_start:desc_end].strip()

        # 謎の [] 囲みを除去
        if description.startswith("[") and description.endswith("]"):
            description = description[1:-1].strip()

        # 不要な記号や空行を除去
        description = re.sub(r"^[。．.\s\(\(（]+", "", description).strip()
        # Markdownの太字装飾を削除（description内）
        description = description.replace("**", "")

        entry = FormerClubEntry(
            name=escape(name), team=escape(team), description=escape(description)
        )

        # 関連性チェック (対戦チームへの言及があるか)
        if is_relevant(description):
            entries.append(entry)
        else:
            logger.warning(
                f"Skipping irrelevant former club entry: {name} (refers to {description[:30]}...)"
            )

    logger.info(f"Parsed {len(entries)} relevant former club entries from LLM output")
    return entries
