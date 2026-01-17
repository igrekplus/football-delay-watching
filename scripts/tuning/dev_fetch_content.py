import json
import logging

import requests
from bs4 import BeautifulSoup

from src.clients.llm_client import LLMClient

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 偽装User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}


def fetch_article_content(url):
    """URLから本文を簡易抽出"""
    try:
        if "facebook.com" in url or "twitter.com" in url or "youtube.com" in url:
            logger.info(f"Skipping social media/video URL: {url}")
            return None

        logger.info(f"Fetching: {url}")
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, "html.parser")

        # 簡易的な本文抽出: <article> または <p> タグの集合
        article = soup.find("article")
        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            # <p>タグを集める
            paragraphs = soup.find_all("p")
            text = "\n".join(
                [
                    p.get_text(strip=True)
                    for p in paragraphs
                    if len(p.get_text(strip=True)) > 50
                ]
            )

        return text[:5000]  # 長すぎるとトークン溢れるのでカット
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def main():
    # articles.json を読み込み
    with open("/tmp/articles.json") as f:
        articles = json.load(f)

    # interview_manager タイプの記事を抽出
    interview_articles = [a for a in articles if a.get("type") == "interview_manager"]

    # 上位3件について本文取得を試みる
    enhanced_articles = []
    for art in interview_articles[:3]:
        full_text = fetch_article_content(art["url"])
        if full_text and len(full_text) > 200:
            print(f"✅ Fetched content for {art['title']} ({len(full_text)} chars)")
            art["content"] = full_text  # contentを上書き
        else:
            print(f"⚠️ Using snippet for {art['title']}")
        enhanced_articles.append(art)

    if not enhanced_articles:
        print("No suitable articles found.")
        return

    # LLMで要約
    client = LLMClient(use_mock=False)  # 実LLMを使用
    summary = client.summarize_interview("Manchester City", enhanced_articles)

    print("\n" + "=" * 50)
    print("ENHANCED SUMMARY (Using Full Content)")
    print("=" * 50)
    print(summary)
    print("=" * 50)


if __name__ == "__main__":
    main()
