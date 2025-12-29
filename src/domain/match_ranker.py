import logging
from typing import List
from config import config
from src.domain.models import MatchData

logger = logging.getLogger(__name__)

class MatchRanker:
    """Domain service for ranking matches."""

    def assign_rank(self, match: MatchData) -> None:
        """Assigns a rank (S, A, None) to a match based on configuration rules."""
        
        # 1. S Rank - Highest priority teams (e.g. Manchester City)
        if any(t in match.home_team or t in match.away_team for t in config.S_RANK_TEAMS):
            match.rank = "S"
            logger.info(f"Assigned S to {match.home_team} vs {match.away_team}")
            return
        
        # 2. A Rank - High priority teams (e.g. Arsenal, Chelsea)
        if any(t in match.home_team or t in match.away_team for t in config.A_RANK_TEAMS):
            match.rank = "A"
            logger.info(f"Assigned A to {match.home_team} vs {match.away_team}")
            return
        
        # 3. A Rank - Japanese players
        # Note: Lineups might not be populated at this stage depending on when ranker is called.
        # In the original flow, rank is assigned after basic match info extraction.
        # Lineups (facts) are usually enriched LATER.
        # However, looking at original MatchProcessor._assign_rank:
        # `all_players = match.home_lineup + match.away_lineup`
        # This implies lineups ARE available match.home_lineup is initialized empty in models?
        # Let's check MatchData model later.
        # Original code accesses home_lineup/away_lineup. If they are empty, this check fails safely.
        
        all_players = match.home_lineup + match.away_lineup
        if any(jp in player for jp in config.JAPANESE_PLAYERS for player in all_players):
            match.rank = "A"
            logger.info(f"Assigned A (Japanese player) to {match.home_team} vs {match.away_team}")
            return
        
        # 4. No special rank
        match.rank = "None"
