import sys
import argparse
import logging
from datetime import datetime
import os
from config import config
from src.match_processor import MatchProcessor
from src.facts_service import FactsService
from src.news_service import NewsService
from src.report_generator import ReportGenerator

# Configure Logging
# Setup Logging with File Output
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

today_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
log_file = os.path.join(log_dir, f"{today_str}.log")

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear existing handlers to avoid duplicates
if logger.hasHandlers():
    logger.handlers.clear()
    
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console Handler
ch = logging.StreamHandler()
ch.setFormatter(formatter)
ch.setLevel(logging.INFO)
logger.addHandler(ch)

# File Handler
fh = logging.FileHandler(log_file, encoding='utf-8')
fh.setFormatter(formatter)
fh.setLevel(logging.INFO)
logger.addHandler(fh)

def main(dry_run=False):
    # The original instruction used `args.dry_run`, but the existing code passes `dry_run` directly.
    # We'll use the `dry_run` parameter for consistency with the existing `main` function signature.
    logger.info(f"Starting viewing guide generation... (Dry Run: {dry_run}, Mock: {config.USE_MOCK_DATA})")
    logger.info(f"Log file created at: {log_file}")
    
    # 1. Match Extraction & Selection
    processor = MatchProcessor()
    matches = processor.run()
    
    if not matches:
        logger.info("No target matches found for today.")
    
    # 2. Facts Acquisition
    facts_service = FactsService()
    facts_service.enrich_matches(matches)
    
    # 3. News Collection & Summarization
    news_service = NewsService()
    news_service.process_news(matches)
    
    # 3.5 YouTube Videos (optional, no error on failure)
    youtube_videos = {}
    try:
        from src.youtube_service import YouTubeService
        youtube_service = YouTubeService()
        youtube_videos = youtube_service.process_matches(matches)
        logger.info(f"YouTube videos fetched for {len(youtube_videos)} matches")
    except Exception as e:
        logger.warning(f"YouTube video fetch failed (continuing without videos): {e}")
    
    # 4. Report Generation
    generator = ReportGenerator()
    report, image_paths = generator.generate(matches, youtube_videos=youtube_videos)
    
    # 5. Email Notification (if enabled)
    if config.GMAIL_ENABLED and config.NOTIFY_EMAIL:
        from src.email_service import send_daily_report
        logger.info(f"Sending email notification to {config.NOTIFY_EMAIL}...")
        if send_daily_report(report, image_paths):
            logger.info("Email sent successfully!")
        else:
            logger.warning("Failed to send email notification.")
    
    # 6. Write API quota to /tmp/quota.txt
    if config.QUOTA_INFO:
        quota_file = "/tmp/quota.txt"
        with open(quota_file, "w", encoding="utf-8") as f:
            for key, info in config.QUOTA_INFO.items():
                f.write(f"{key}: {info}\n")
        logger.info(f"Quota info written to {quota_file}")
    
    # 7. Cache Warming (if quota available and GCS enabled)
    remaining_quota = 0
    
    # Get remaining quota from QUOTA_INFO or by checking API
    if "API-Football" in config.QUOTA_INFO:
        quota_str = config.QUOTA_INFO.get("API-Football", "")
        if "Remaining:" in quota_str:
            try:
                remaining_quota = int(quota_str.split("Remaining:")[1].split("/")[0].strip())
            except (ValueError, IndexError):
                pass
    
    # If no quota info (all cache hits), check directly via API
    if remaining_quota == 0 and not config.USE_MOCK_DATA:
        import requests
        try:
            url = "https://api-football-v1.p.rapidapi.com/v3/status"
            headers = {
                "X-RapidAPI-Key": config.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                account = data.get("response", {}).get("subscription", {})
                requests_info = data.get("response", {}).get("requests", {})
                limit = requests_info.get("limit_day", 100)
                current = requests_info.get("current", 0)
                remaining_quota = limit - current
                logger.info(f"API-Football quota check: {remaining_quota}/{limit} remaining")
        except Exception as e:
            logger.warning(f"Failed to check API quota: {e}")
    
    if remaining_quota > 0:
        from src.cache_warmer import run_cache_warming
        logger.info(f"Starting cache warming with {remaining_quota} remaining quota...")
        result = run_cache_warming(remaining_quota)
        logger.info(f"Cache warming result: {result}")
    else:
        logger.info("Skipping cache warming: no quota info available")
    
    logger.info("Done.")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run)
