"""
Parsers module for extracting structured data from LLM outputs.
"""

from .former_club_parser import FormerClubEntry, parse_former_club_text
from .key_player_parser import KeyPlayer, parse_key_player_text
from .matchup_parser import PlayerMatchup, parse_matchup_text

__all__ = [
    "parse_matchup_text",
    "PlayerMatchup",
    "parse_key_player_text",
    "KeyPlayer",
    "parse_former_club_text",
    "FormerClubEntry",
]
