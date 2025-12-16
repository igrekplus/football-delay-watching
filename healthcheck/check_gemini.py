#!/usr/bin/env python3
"""
Gemini API ヘルスチェック

使用方法:
    python healthcheck/check_gemini.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def check_gemini():
    """Gemini APIのステータスを確認"""
    load_dotenv()
    
    api_key = os.getenv('GOOGLE_API_KEY')
    
    print("=" * 50)
    print("📊 Gemini API ステータス確認")
    print("=" * 50)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not api_key:
        print("❌ GOOGLE_API_KEY が設定されていません")
        return False
    
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-latest')
        
        # シンプルなテストプロンプト
        response = model.generate_content("Say 'Hello' in one word.")
        
        print(f"📡 レスポンス: {response.text.strip()}")
        print()
        print("✅ Gemini API: 正常")
        print("   ⚠️ クォータ: 1,500リクエスト/日程度 (無料枠)")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            print("⛔ Gemini API: クォータ超過")
            print("   → 数時間待つか、別のAPIキーを使用してください。")
        elif "401" in error_msg or "403" in error_msg:
            print("❌ Gemini API: 認証エラー")
            print(f"   → {error_msg}")
        else:
            print(f"❌ Gemini API: エラー")
            print(f"   → {error_msg}")
        return False


if __name__ == "__main__":
    success = check_gemini()
    print()
    print("=" * 50)
    sys.exit(0 if success else 1)
