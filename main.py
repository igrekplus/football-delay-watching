import sys
import argparse
import logging
from datetime import datetime
import os
from config import config
from src.workflows.generate_guide_workflow import GenerateGuideWorkflow

# Configure Logging
log_dir = "logs/execution"
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
    logger.info(f"Log file created at: {log_file}")
    
    workflow = GenerateGuideWorkflow()
    workflow.run(dry_run=dry_run)

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run)
