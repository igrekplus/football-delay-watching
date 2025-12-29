import logging
import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from config import config
from src.clients.api_football_client import ApiFootballClient
from src.domain.match_ranker import MatchRanker
from src.domain.match_selector import MatchSelector
from src.domain.models import MatchData
from src.utils.execution_policy import ExecutionPolicy
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_api_client():
    logger.info("Verifying ApiFootballClient...")
    if config.USE_MOCK_DATA:
        logger.info("Skipping API calls in Mock Mode (enable DEBUG_MODE=True USE_MOCK_DATA=False to test real API)")
        return

    client = ApiFootballClient()
    # Test fixtures (should use cached data if available or make a call)
    # Using a past date and league (EPL)
    try:
        data = client.get_fixtures(39, 2024, "2024-12-01")
        if data:
            logger.info("ApiFootballClient.get_fixtures: OK")
        else:
            logger.warning("ApiFootballClient.get_fixtures: Returned empty/None")
            
        # Test Squad (Man City id=50)
        squad = client.get_squad(50, "Manchester City")
        if squad:
             logger.info("ApiFootballClient.get_squad: OK")
        else:
             logger.warning("ApiFootballClient.get_squad: Returned empty/None")
             
    except Exception as e:
        logger.error(f"ApiFootballClient Test Failed: {e}")

def verify_domain_logic():
    logger.info("Verifying Domain Logic...")
    ranker = MatchRanker()
    selector = MatchSelector()
    
    # Create dummy matches
    m1 = MatchData(id="1", home_team="Manchester City", away_team="Everton", competition="EPL", kickoff_jst="2024/01/01 20:00 JST", kickoff_local="", rank="None", venue="", referee="", home_logo="", away_logo="", kickoff_at_utc=datetime.now())
    m2 = MatchData(id="2", home_team="Brighton", away_team="Luton", competition="EPL", kickoff_jst="2024/01/01 20:00 JST", kickoff_local="", rank="None", venue="", referee="", home_logo="", away_logo="", kickoff_at_utc=datetime.now())
    
    # Rank
    ranker.assign_rank(m1)
    logger.info(f"Match 1 Rank: {m1.rank} (Expected S)")
    
    ranker.assign_rank(m2)
    logger.info(f"Match 2 Rank: {m2.rank} (Expected None)")
    
    # Select (Limit 1 for test?)
    # config.MATCH_LIMIT is dynamic.
    matches = [m1, m2]
    selected = selector.select(matches)
    
    logger.info(f"Selected {len(selected)} matches. Limit is {config.MATCH_LIMIT}")
    for m in selected:
        logger.info(f" - {m.home_team} vs {m.away_team} (Target: {m.is_target}, Reason: {m.selection_reason})")

def verify_execution_policy():
    logger.info("Verifying ExecutionPolicy...")
    policy = ExecutionPolicy(time_limit_hour=9)
    
    # Check quota check
    can_run = policy.should_continue(remaining_quota=100)
    logger.info(f"Policy check (Quota 100): {can_run}")
    
    cant_run = policy.should_continue(remaining_quota=0)
    logger.info(f"Policy check (Quota 0): {cant_run}")

if __name__ == "__main__":
    verify_domain_logic()
    verify_execution_policy()
    verify_api_client()
