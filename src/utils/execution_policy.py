import logging
from datetime import datetime
import pytz
from config import config

logger = logging.getLogger(__name__)

class ExecutionPolicy:
    """Manages execution constraints such as time limits and quota thresholds."""

    def __init__(self, time_limit_hour: int = 9, time_limit_minute: int = 0):
        self.limit_hour = time_limit_hour
        self.limit_minute = time_limit_minute
        self.tz = pytz.timezone('Asia/Tokyo')

    def should_continue(self, remaining_quota: int) -> bool:
        """
        Determines if execution should continue based on quota and time.
        Retuns True if both quota is sufficient and time is within limits.
        """
        if remaining_quota < config.CACHE_WARMING_QUOTA_THRESHOLD:
            logger.info(f"Stopping: quota {remaining_quota} < threshold {config.CACHE_WARMING_QUOTA_THRESHOLD}")
            return False
            
        if not self.is_within_time_limit():
            logger.info("Stopping: Approaching time limit.")
            return False
            
        return True

    def is_within_time_limit(self) -> bool:
        """Checks if current time is before the limit (with 5 min buffer)."""
        now = datetime.now(self.tz)
        
        # Buffer: stop 5 minutes before the limit
        buffer_minutes = 5
        
        limit_time = now.replace(hour=self.limit_hour, minute=self.limit_minute, second=0, microsecond=0)
        
        # If current hour is significantly past limit (e.g. running at 10am), handling depends on "reset time".
        # The original code logic: if now.hour >= 8 and now.minute >= 55: stop.
        # This implies the job runs BEFORE 9am.
        # If limit is 9:00, stop at 8:55.
        
        # Effective limit with buffer
        effective_limit_minute = self.limit_minute - buffer_minutes
        effective_limit_hour = self.limit_hour
        
        if effective_limit_minute < 0:
            effective_limit_minute += 60
            effective_limit_hour -= 1
            
        # Simple check: if current time is "late" relative to intended window.
        # Assuming the job runs in the early morning.
        
        if now.hour > effective_limit_hour:
             return False
        if now.hour == effective_limit_hour and now.minute >= effective_limit_minute:
             return False
             
        return True
