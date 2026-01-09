import logging
from typing import List
from config import config
from src.domain.models import MatchAggregate

logger = logging.getLogger(__name__)

class MatchSelector:
    """Domain service for selecting matches to report on."""

    def select(self, matches: List[MatchAggregate]) -> List[MatchAggregate]:
        """
        Selects matches based on rank and configured limits.
        
        Selection Logic:
        1. Prioritize matches with Rank != "None".
        2. If count < MATCH_LIMIT, fill with Rank == "None" matches (fillers).
        3. Cap total at MATCH_LIMIT.
        """
        rank_order = {"Absolute": 0, "S": 1, "A": 2, "None": 3}
        
        # Sort logic
        def sort_key(m: MatchAggregate):
            r_score = rank_order.get(m.core.rank, 99)
            # Competition priority: CL > LALIGA > EPL > COPA > FA > EFL
            comp_priority = {"CL": 0, "LALIGA": 1, "EPL": 2, "COPA": 3, "FA": 4, "EFL": 5}
            comp_score = comp_priority.get(m.core.competition, 99)
            return (r_score, comp_score)

        sorted_matches = sorted(matches, key=sort_key)
        limit = config.MATCH_LIMIT
        
        high_rank_matches = [m for m in sorted_matches if m.core.rank != "None"]
        low_rank_matches = [m for m in sorted_matches if m.core.rank == "None"]
        
        selected_count = 0
        result = []
        
        # 1. Select High Rank Matches
        for match in high_rank_matches:
            if selected_count < limit:
                match.core.is_target = True
                match.core.selection_reason = None
                selected_count += 1
            else:
                match.core.is_target = False
                match.core.selection_reason = "Out of quota"
            result.append(match)
        
        # 2. Fill with Low Rank Matches
        for match in low_rank_matches:
            if selected_count < limit:
                match.core.is_target = True
                match.core.selection_reason = "Included as filler"
                logger.info(f"Including low-rank match as filler: {match.core.home_team} vs {match.core.away_team}")
                selected_count += 1
            else:
                match.core.is_target = False
                match.core.selection_reason = "Low rank"
            result.append(match)
        
        logger.info(f"Selected {selected_count} matches (limit: {limit})")
        return result
