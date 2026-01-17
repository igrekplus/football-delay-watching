"""
Parsers module for extracting structured data from LLM outputs.
"""
from .matchup_parser import parse_matchup_text, PlayerMatchup
from .key_player_parser import parse_key_player_text, KeyPlayer
from .former_club_parser import parse_former_club_text, FormerClubEntry

__all__ = [
    'parse_matchup_text', 'PlayerMatchup', 
    'parse_key_player_text', 'KeyPlayer',
    'parse_former_club_text', 'FormerClubEntry'
]
