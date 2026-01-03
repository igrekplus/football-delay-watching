
import os
import sys
import google.generativeai as genai
from config import config

# プロジェクトルートにパスを通す
sys.path.append(os.getcwd())

import argparse

def main():
    api_key = config.GOOGLE_API_KEY
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in config.")
        return

    parser = argparse.ArgumentParser(description='Gemini Grounding PoC')
    parser.add_argument('--home', type=str, default="Bournemouth", help='Home team')
    parser.add_argument('--away', type=str, default="Arsenal", help='Away team')
    args = parser.parse_args()

    team_name = args.home
    opponent = args.away

    genai.configure(api_key=api_key)

    # Search Grounding対応モデル
    # protosを直接使用してツールを定義 (google_search_retrievalを使用)
    tool = genai.protos.Tool(
        google_search_retrieval=genai.protos.GoogleSearchRetrieval(
            dynamic_retrieval_config=genai.protos.DynamicRetrievalConfig(
                mode=genai.protos.DynamicRetrievalConfig.Mode.MODE_DYNAMIC,
                dynamic_threshold=0.3
            )
        )
    )
    model = genai.GenerativeModel('models/gemini-pro', tools=[tool])

    # 検索クエリを内包させたプロンプト
    prompt = f"""
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
    - 文字数: 800-1000字程度
    
    ## 出力形式
    - 本文のみ
    """

    print(f"Generating content with Grounding for {team_name} vs {opponent}...")
    try:
        response = model.generate_content(prompt)
        
        print("\\n" + "="*50)
        print("GEMINI GROUNDING RESPONSE")
        print("="*50)
        print(response.text)
        print("="*50)
        
        # 参照元情報の確認（もしあれば）
        if response.candidates[0].grounding_metadata.search_entry_point:
            print("\\nGrounding Metadata:")
            print(response.candidates[0].grounding_metadata.search_entry_point.rendered_content)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
