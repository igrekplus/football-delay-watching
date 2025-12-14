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
log_dir = os.path.join(config.OUTPUT_DIR, "raw-data")
os.makedirs(log_dir, exist_ok=True)

today_str = datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(log_dir, f"{today_str}_log.md")

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

# Add Header to Log File
with open(log_file, 'a', encoding='utf-8') as f:
    f.write(f"\n\n# Execution Log: {today_str}\n\n")

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
    generator.generate(matches)
    
    logger.info("Done.")

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run)
