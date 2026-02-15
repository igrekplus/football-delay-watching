from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import escape

logger = logging.getLogger(__name__)


@dataclass
class PlayerMatchup:
    """選手マッチアップ情報（最大4名対応）"""

    header: str  # "🇯🇵 Japan" や "1." など
    players: list[tuple[str, str]]  # [(選手名, チーム名), ...] 最大4名
    description: str


def _extract_players(text: str) -> list[tuple]:
    """
    テキストから選手名とチーム名を抽出
    形式: **選手名** (チーム名) または **選手名**（チーム名）
    """
    # ボールド選手名 + 括弧チーム名のパターン（全角/半角両対応）
    pattern = r"\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]"
    return re.findall(pattern, text)


def parse_matchup_text(llm_output: str) -> list[PlayerMatchup]:
    """
    LLM出力から選手マッチアップ情報を抽出
    同国対決、キーマッチアップの両方に対応（柔軟なフォーマット対応）
    """
    if not llm_output:
        return []

    logger.info(f"[MATCHUP] Input text length: {len(llm_output)} chars")

    matchups = []

    # 1. まず行単位で処理（1行に1マッチアップの場合）
    # ヘッダー行（国旗 + 国名）の検出
    header_line_pattern = (
        r"^([🇦-🇿🏴\U0001f1e6-\U0001f1ff\U000e0020-\U000e007f]+)\s*\*\*([^*]+)\*\*"
    )

    lines = llm_output.split("\n")
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
                result = _process_section(current_header, "\n".join(current_content))
                if result:
                    matchups.append(result)

            # 太字装飾 ** を削除
            current_header = f"{header_match.group(1)} {header_match.group(2)}"
            # 同じ行に選手情報がある場合
            remaining = line[header_match.end() :].strip()
            current_content = [remaining] if remaining else []
        else:
            current_content.append(line)

    # 最後のセクションを処理
    if current_content:
        result = _process_section(current_header, "\n".join(current_content))
        if result:
            matchups.append(result)

    # 2. もしマッチアップが見つからなかった場合、vsパターンで直接検索
    if not matchups:
        logger.info(
            "[MATCHUP] Header pattern found 0 matchups, trying vs-pattern fallback"
        )
        vs_pattern = r"\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]\s*(?:vs|と)\s*\*\*([^*]+)\*\*\s*[（\(]([^）\)]+)[）\)]"
        for match in re.finditer(vs_pattern, llm_output):
            # 説明文は選手情報の後ろのテキスト。次のマッチアップの開始または改行2つまで取得
            desc_start = match.end()
            # 次の ** か 箇条書き番号(\d+\.) を探す
            next_start_match = re.search(
                r"\n\s*(?:\*\*|\d+\.)", llm_output[desc_start:]
            )
            if next_start_match:
                desc_end = desc_start + next_start_match.start()
            else:
                desc_end = len(llm_output)

            description = re.sub(
                r"^[。．.\s\(\(（vs:：と]+", "", llm_output[desc_start:desc_end]
            ).strip()

            # 全てのフィールドから ** を削除
            matchups.append(
                PlayerMatchup(
                    header="",
                    players=[
                        (
                            escape(match.group(1).strip()),
                            escape(match.group(2).strip()),
                        ),
                        (
                            escape(match.group(3).strip()),
                            escape(match.group(4).strip()),
                        ),
                    ],
                    description=escape(description.replace("**", "")),
                )
            )

    logger.info(f"[MATCHUP] Parsed {len(matchups)} matchups from LLM output")
    return matchups


def _process_section(header: str, content: str) -> PlayerMatchup | None:
    """セクション（ヘッダー + コンテンツ）から1つのマッチアップを抽出（最大4名）"""
    players = _extract_players(content)

    if len(players) < 2:
        logger.debug(f"Less than 2 players found in section: {content[:50]}...")
        return None

    # 最大4選手を取得
    players_limited = players[:4]

    # 説明文を抽出（全選手情報を除去した残り）
    description = content
    for name, team in players_limited:
        pattern = rf"\*\*{re.escape(name)}\*\*\s*[（\(]{re.escape(team)}[）\)]"
        description = re.sub(pattern, "", description)

    # 「は」「と」「の」「の対決。/の対決」などの接続詞と重複改行を整理
    # 自然文形式での残骸を除去
    description = re.sub(
        r"^\s*(?:は[、,]?\s*|と\s*|の\s*|vs\s*[:：]?\s*)", "", description
    )
    # 「選手A (チームA) と 選手B (チームB) の対決。」のような場合の「の対決」部分を削除
    description = re.sub(
        r"^\s*(?:の対決[。．,、\s]*|のマッチアップ[。．,、\s]*)", "", description
    )
    description = re.sub(r"^[。．.,、\s\(\(（]+", "", description).strip()

    # 全てのフィールドから ** を削除
    return PlayerMatchup(
        header=escape(header.replace("**", "")) if header else "",
        players=[(escape(n.strip()), escape(t.strip())) for n, t in players_limited],
        description=escape(description.replace("**", "")),
    )
