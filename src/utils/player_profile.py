import re

PROFILE_DETAIL_FORMAT_DEFAULT = "labelled_lines_v1"


def build_player_profile_id(player_name: str) -> str:
    """選手名から DOM 用の安定したプロフィールIDを生成する。"""
    slug = re.sub(r"[^a-z0-9]+", "-", player_name.lower()).strip("-")
    if not slug:
        slug = "player"
    return f"player-profile-{slug}"


def parse_player_profile_sections(
    profile: dict[str, str] | None,
) -> list[dict[str, str]]:
    """
    プロフィール文字列を、表示用セクションの配列に変換する。

    `labelled_lines_v1` では `ラベル::本文` の複数行を想定する。
    ラベルなし行は直前セクションへの追記、先頭行であれば「詳細」として扱う。
    """
    if not profile:
        return []

    detail = (profile.get("detail") or "").strip()
    if not detail:
        return []
    detail = detail.replace("\\n", "\n")

    format_name = (profile.get("format") or PROFILE_DETAIL_FORMAT_DEFAULT).strip()
    if format_name != PROFILE_DETAIL_FORMAT_DEFAULT:
        return [{"label": "詳細", "body": detail}]

    sections: list[dict[str, str]] = []
    for raw_line in detail.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if "::" in line:
            label, body = line.split("::", 1)
            sections.append(
                {
                    "label": label.strip() or "詳細",
                    "body": body.strip(),
                }
            )
            continue

        if sections:
            current_body = sections[-1]["body"]
            sections[-1]["body"] = (
                f"{current_body}\n{line}".strip() if current_body else line
            )
        else:
            sections.append({"label": "詳細", "body": line})

    return [section for section in sections if section.get("body")]
