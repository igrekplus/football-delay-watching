import logging
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_llm_integration():
    print("=== Verifying LLMClient Integration (summarize_interview) ===")

    from src.clients.llm_client import LLMClient

    # 1. Initialize Client (use_mock=False to test real API)
    client = LLMClient(use_mock=False)

    team_name = "Manchester City"
    # Groundingプロンプトでは articles は検索キーワードのヒントには使っていないが、
    # 引数としては必要。
    dummy_articles = [
        {
            "content": "Dummy content",
            "title": "Dummy Title",
            "source": "Dummy Source",
            "url": "http://dummy.com",
        }
    ]

    print(f"\nCalling summarize_interview for {team_name}...")
    print("Expected behavior: Should call GeminiRestClient and perform Google Search.")

    try:
        summary = client.summarize_interview(team_name, dummy_articles)

        print("\n" + "=" * 50)
        print("GENERATED SUMMARY")
        print("=" * 50)
        print(summary)
        print("=" * 50)

        if "エラーにつき" in summary:
            print("\n[FAIL] Returned error message.")
        elif len(summary) > 100:
            print("\n[SUCCESS] Summary generated successfully via LLMClient.")
        else:
            print("\n[WARNING] Summary seems too short or empty.")

    except Exception as e:
        print(f"\n[FAIL] Exception occurred: {e}")


if __name__ == "__main__":
    verify_llm_integration()
