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
    
    # 4. Report Generation
    generator = ReportGenerator()
    report, image_paths = generator.generate(matches)
    
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
    
    logger.info("Done.")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run)
