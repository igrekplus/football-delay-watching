import logging
from typing import List
from config import config
from src.domain.models import MatchAggregate

logger = logging.getLogger(__name__)

class MatchRanker:
    """Domain service for ranking matches."""

    def assign_rank(self, match: MatchAggregate) -> None:
        """Assigns a rank (S, A, None) to a match based on configuration rules."""
        
        # 1. S Rank - Highest priority teams (e.g. Manchester City)
        if any(t in match.core.home_team or t in match.core.away_team for t in config.S_RANK_TEAMS):
            match.core.rank = "S"
            logger.info(f"Assigned S to {match.core.home_team} vs {match.core.away_team}")
            return
        
        # 2. A Rank - High priority teams (e.g. Arsenal, Chelsea)
        if any(t in match.core.home_team or t in match.core.away_team for t in config.A_RANK_TEAMS):
            match.core.rank = "A"
            logger.info(f"Assigned A to {match.core.home_team} vs {match.core.away_team}")
            return
        
        # 3. A Rank - Japanese players
        # Note: Lineups might not be populated at this stage depending on when ranker is called.
        all_players = match.facts.home_lineup + match.facts.away_lineup
        if any(jp in player for jp in config.JAPANESE_PLAYERS for player in all_players):
            match.core.rank = "A"
            logger.info(f"Assigned A (Japanese player) to {match.core.home_team} vs {match.core.away_team}")
            return
        
        # 4. No special rank
        match.core.rank = "None"
