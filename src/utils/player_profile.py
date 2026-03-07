import re

PROFILE_DETAIL_FORMAT_DEFAULT = "labelled_lines_v1"
SINGLE_CARD_LABELS = {"経歴"}


def build_player_profile_id(player_name: str) -> str:
    """選手名から DOM 用の安定したプロフィールIDを生成する。"""
    slug = re.sub(r"[^a-z0-9]+", "-", player_name.lower()).strip("-")
    if not slug:
        slug = "player"
    return f"player-profile-{slug}"


def build_player_profile_slug(player_id: int, player_name: str) -> str:
    """player_id ベースの固定URL用 slug（例: 41621）"""
    return str(player_id)


def build_player_profile_url(player_id: int, player_name: str) -> str:
    """選手プロフィールHTMLの相対URL（例: /player-profiles/41621.html）"""
    return f"/player-profiles/{build_player_profile_slug(player_id, player_name)}.html"


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


def validate_player_profile_sections(
    sections: list[dict[str, str]],
    *,
    player_id: str | int | None = None,
    player_name: str | None = None,
) -> None:
    """プロフィール表示上、分割を許容しないラベルの重複を検知する。"""
    label_counts: dict[str, int] = {}
    for section in sections:
        label = (section.get("label") or "").strip()
        if not label:
            continue
        label_counts[label] = label_counts.get(label, 0) + 1

    duplicated_labels = sorted(
        label
        for label, count in label_counts.items()
        if label in SINGLE_CARD_LABELS and count > 1
    )
    if not duplicated_labels:
        return

    context_parts = []
    if player_id is not None:
        context_parts.append(f"player_id={player_id}")
    if player_name:
        context_parts.append(f"player_name={player_name}")
    context = f" ({', '.join(context_parts)})" if context_parts else ""

    raise ValueError(
        "Profile contains labels that must stay in a single card"
        f"{context}: {', '.join(duplicated_labels)}. "
        "Use one `経歴::` line and continue the timeline on following unlabeled lines."
    )
