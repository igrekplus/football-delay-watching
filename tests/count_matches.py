import os
import sys

sys.path.append(os.getcwd())

# 環境変数を設定（configインポート前またはプロパティアクセス前に有効）
os.environ["TARGET_DATE"] = "2026-01-10"
os.environ["USE_MOCK_DATA"] = "False"

from config import config
from src.match_processor import MatchProcessor

print(f"Checking matches for target date: {config.TARGET_DATE}")
processor = MatchProcessor()
matches = processor.extract_matches()
print(f"Total matches found: {len(matches)}")
for m in matches:
    print(f"- {m.core.home_team} vs {m.core.away_team} ({m.core.competition})")
