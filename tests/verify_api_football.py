import os
import requests
import json
from dotenv import load_dotenv

# Load .env
load_dotenv()

def verify_api_football():
    print("=== Verifying API-Football (RapidAPI) ===")
    
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("[ERROR] RAPIDAPI_KEY is incomplete in .env")
        return

    url = "https://api-football-v1.p.rapidapi.com/v3/leagues"
    params = {"country": "England", "season": "2023"} # Use known params to limit output
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        
        # Check specific API status field
        if "response" in data and "account" in data["response"]:
            account = data["response"]["account"]
            print(f"[SUCCESS] Account: {account['firstname']} {account['lastname']}")
            print(f"          Email: {account['email']}")
            print(f"          Requests: {data['response']['requests']['current']} / {data['response']['requests']['limit_day']}")
        elif "message" in data:
             print(f"[API MESSAGE] {data['message']}")
        else:
            print("[INFO] Raw Response:")
            print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")

if __name__ == "__main__":
    verify_api_football()
