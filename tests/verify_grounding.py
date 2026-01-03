import sys
import os
import logging
from config import config

# Add project root to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_grounding():
    print("=== Verifying Gemini Rest Client (Grounding) ===")
    
    from src.clients.gemini_rest_client import GeminiRestClient
    
    # 1. Initialize Client
    try:
        client = GeminiRestClient()
        print("[OK] Client initialized")
    except Exception as e:
        print(f"[FAIL] Client initialization failed: {e}")
        return

    # 2. Test Grounding (Manchester City vs Arsenal is usually a good test case for abundant news)
    # Using a fake future match context or general query
    prompt = """
Task: Manchester Cityのグアルディオラ監督の最新の記者会見の発言を検索し、要約してください。
特に怪我人に関する情報を重点的に探してください。

## 検索指示
- "Pep Guardiola press conference quotes latest"
- "Manchester City injury news latest"
"""
    
    print(f"\nSending prompt:\n{prompt}")
    print("\nWaiting for Gemini response (this implies Google Search)...")
    
    try:
        result = client.generate_content_with_grounding(prompt)
        print("\n" + "="*50)
        print("GENERATED CONTENT")
        print("="*50)
        print(result)
        print("="*50)
        
        if len(result) > 100:
            print("\n[SUCCESS] Content generated successfully.")
        else:
            print("\n[WARNING] Content seems too short.")
            
    except Exception as e:
        print(f"\n[FAIL] Generation failed: {e}")

if __name__ == "__main__":
    verify_grounding()
