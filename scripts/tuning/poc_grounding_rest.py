import argparse
import json
import os
import sys

import requests

from config import config

# プロジェクトルートにパスを通す
sys.path.append(os.getcwd())


def main():
    api_key = config.GOOGLE_API_KEY
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in config.")
        return

    parser = argparse.ArgumentParser(description="Gemini Grounding PoC (REST API)")
    parser.add_argument("--home", type=str, default="Bournemouth", help="Home team")
    parser.add_argument("--away", type=str, default="Arsenal", help="Away team")
    args = parser.parse_args()

    team_name = args.home
    opponent = args.away

    # モデルとエンドポイント
    # gemini-2.0-flash-exp を使用
    model_name = "gemini-2.0-flash-exp"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    # プロンプト
    prompt_text = f"""
    Task: {team_name}の監督と{opponent}の監督が、この試合（{team_name} vs {opponent}）に関して語った最新のコメントや記者会見の内容を検索し、日本語で要約してください。

    ## 検索指示
    - "{team_name} manager press conference quotes vs {opponent}"
    - "{opponent} manager press conference quotes vs {team_name}"
    - などのクエリで最新情報を探してください。
    - 直近（24-48時間以内）の情報を優先してください。

    ## 要約の要件
    - 監督の具体的な発言があれば、可能な限りカギカッコ「」で原文のニュアンスを残して引用してください。
    - 試合結果（スコアなど）が既に判明している場合は、**絶対に結果には触れず**、試合前のコメントとして構成してください。
    - 確実な情報源（BBC, Sky Sports, 公式サイト等）に基づいていることを重視してください。
    - **文字数: 1800-2000字程度（非常に詳細に記述してください）**
    - 以下の点について詳しく記述してください：
        - 怪我人・復帰選手の詳細な状況
        - 相手チームの戦術や選手に対する具体的な評価・分析
        - 今後の過密日程やシーズン全体の展望に対する言及
        - 記者との質疑応答における興味深いやり取り

    ## 出力形式
    - 本文のみ
    """

    # リクエストペイロード
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    data = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "tools": [
            {
                "googleSearch": {}  # REST API用の指定
            }
        ],
    }

    print(f"Generating content using REST API ({model_name}) with Grounding...")

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code == 200:
            result = response.json()

            # レスポンス解析
            try:
                candidate = result["candidates"][0]
                content_parts = candidate["content"]["parts"]
                text = "".join([part.get("text", "") for part in content_parts])

                print("\n" + "=" * 50)
                print("GEMINI GROUNDING RESPONSE (REST API)")
                print("=" * 50)
                print(text)
                print("=" * 50)

                # Grounding Metadata
                if "groundingMetadata" in candidate:
                    print("\nGrounding Metadata Found.")
                    meta = candidate["groundingMetadata"]
                    if "searchEntryPoint" in meta:
                        print(
                            "Search Entry Point:",
                            meta["searchEntryPoint"].get("renderedContent"),
                        )
                    if "groundingChunks" in meta:
                        print(
                            f"Grounding Chunks: {len(meta['groundingChunks'])} chunks used."
                        )

            except (KeyError, IndexError) as e:
                print(f"Failed to parse response structure: {e}")
                print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            print(f"Error: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    main()
