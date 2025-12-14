import os
import requests
import json
from dotenv import load_dotenv

# Load .env
load_dotenv()

def verify_google_search():
    print("=== Verifying Google Custom Search API ===")
    
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    if not api_key or not cx:
        print("[ERROR] GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_ENGINE_ID is incomplete in .env")
        return

    url = "https://www.googleapis.com/customsearch/v1"
    query = "Manchester City match preview"
    
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        
        if "items" in data:
            item = data["items"][0]
            print(f"[SUCCESS] Found {len(data['items'])} items.")
            print(f"          Top Result Title: {item.get('title')}")
            print(f"          Link: {item.get('link')}")
        elif "error" in data:
             print(f"[ERROR] API Error: {data['error']['message']}")
        else:
            print("[INFO] No items found or unknown format.")
            print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    verify_google_search()
