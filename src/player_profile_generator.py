import logging
import os

from src.domain.models import MatchAggregate
from src.template_engine import render_template
from src.utils.player_profile import (
    build_player_profile_slug,
    parse_player_profile_sections,
    validate_player_profile_sections,
)

logger = logging.getLogger(__name__)


def write_player_profile_files(
    match: MatchAggregate, output_dir: str = "public/player-profiles"
) -> list[str]:
    """
    \u9078\u624b\u30d7\u30ed\u30d5\u30a3\u30fc\u30ebHTML\u3092\u9078\u624b\u5358\u4f4d\u3067\u51fa\u529b\u3059\u308b\u3002
    \u30d5\u30a1\u30a4\u30eb\u540d: {player_id}-{slug}.html
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    generated_files = []

    # name -> player_id \u306e\u30de\u30c3\u30d7\u3092\u5229\u7528
    player_id_map = match.facts.player_id_map

    for player_name, profile in match.facts.player_profiles.items():
        player_id = player_id_map.get(player_name)
        if not player_id:
            logger.warning(
                f"Skipping profile generation for {player_name}: player_id not found in map"
            )
            continue

        sections = parse_player_profile_sections(profile)
        if not sections:
            continue
        validate_player_profile_sections(
            sections,
            player_id=player_id,
            player_name=player_name,
        )

        # \u30c6\u30f3\u30d7\u30ec\u30fc\u30c8\u3092\u30ec\u30f3\u30c0\u30ea\u30f3\u30b0\uff08standalone\u7528\uff09
        html_fragment = render_template(
            "partials/player_profile_standalone.html", sections=sections
        )

        # \u30d5\u30a1\u30a4\u30eb\u540d\u6c7a\u5b9a
        slug = build_player_profile_slug(player_id, player_name)
        filename = f"{slug}.html"
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_fragment)
            generated_files.append(filepath)
            logger.debug(f"Generated standalone profile: {filepath}")
        except Exception as e:
            logger.error(f"Error writing profile file {filepath}: {e}")

    return generated_files
