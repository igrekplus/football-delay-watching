import os
import sys
import re
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# 強制的にメール送信有効化
os.environ['GMAIL_ENABLED'] = 'True'
os.environ['NOTIFY_EMAIL'] = 'nakame.kate@gmail.com'

from src.email_service import send_daily_report
from config import config

import logging
logging.basicConfig(level=logging.INFO)

def main():
    report_path = Path("reports_debug/2025-12-14.md")
    
    if not report_path.exists():
        print(f"Error: {report_path} not found.")
        return

    print(f"Reading report: {report_path}")
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 画像パスの抽出
    # パターン: ![alt](path)
    image_paths = []
    matches = re.findall(r'!\[.*?\]\((.*?)\)', content)
    
    print(f"Found {len(matches)} images in markdown.")
    
    for relative_path in matches:
        # レポートファイルのディレクトリ基準でパスを解決
        abs_path = (report_path.parent / relative_path).resolve()
        
        if abs_path.exists():
            image_paths.append(str(abs_path))
            print(f"  - Image found: {abs_path}")
        else:
            print(f"  - Image NOT found: {relative_path} (checked {abs_path})")

    print("\nSending email...")
    success = send_daily_report(content, image_paths)
    
    if success:
        print("✅ Email sent successfully.")
    else:
        print("❌ Email sending failed.")

if __name__ == "__main__":
    main()
