from __future__ import annotations

import logging
import sys

from src.formatters.player_formatter import PlayerFormatter
from src.parsers.former_club_parser import parse_former_club_text

# ログ設定
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")


def test_logs():
    print("--- Testing FormerClubParser Log ---")
    llm_output = "**John Doe** (Team A)\nLegendary player.\n**John Doe** (Team A)\nDuplicate entry."
    parse_former_club_text(llm_output)

    print("\n--- Testing PlayerFormatter Log ---")
    formatter = PlayerFormatter()
    formatter.format_player_cards(["Player 1"], "4-3-3", "Test Team")


if __name__ == "__main__":
    test_logs()
