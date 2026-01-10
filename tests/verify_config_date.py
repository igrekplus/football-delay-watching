
import os
import sys
# Set env vars to simulate debug mode
os.environ["DEBUG_MODE"] = "True"
os.environ["USE_MOCK_DATA"] = "False"

# Clear TARGET_DATE if set in env (to test default)
if "TARGET_DATE" in os.environ:
    del os.environ["TARGET_DATE"]

sys.path.append(os.getcwd())
from config import config
from datetime import datetime, timedelta
import pytz

jst = pytz.timezone('Asia/Tokyo')
now_jst = datetime.now(jst)
expected_date = now_jst - timedelta(days=1)
actual_date = config.TARGET_DATE

print(f"Current JST: {now_jst}")
print(f"Expected Default TARGET_DATE: {expected_date}")
print(f"Actual config.TARGET_DATE:   {actual_date}")

# Check if days match (ignoring microseconds/seconds diffs)
if actual_date.date() == expected_date.date():
    print("SUCCESS: Default TARGET_DATE is correctly set to yesterday.")
else:
    print("FAILURE: Default TARGET_DATE does not match yesterday.")
