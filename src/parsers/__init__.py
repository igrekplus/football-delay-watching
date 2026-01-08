"""
Parsers module for extracting structured data from LLM outputs.
"""
from .matchup_parser import parse_matchup_text, PlayerMatchup

__all__ = ['parse_matchup_text', 'PlayerMatchup']
