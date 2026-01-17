#!/usr/bin/env python3
"""
Gmail API ヘルスチェック

使用方法:
    python healthcheck/check_gmail.py
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv


def check_gmail():
    """Gmail APIのステータスを確認"""
    load_dotenv()

    gmail_token = os.getenv("GMAIL_TOKEN")
    gmail_credentials = os.getenv("GMAIL_CREDENTIALS")
    gmail_enabled = os.getenv("GMAIL_ENABLED", "False").lower() == "true"
    notify_email = os.getenv("NOTIFY_EMAIL")

    print("=" * 50)
    print("📊 Gmail API ステータス確認")
    print("=" * 50)
    print(f"🕐 確認日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print(f"📧 GMAIL_ENABLED: {gmail_enabled}")
    print(f"📬 NOTIFY_EMAIL: {notify_email or '(未設定)'}")
    print()

    # Check credentials
    if not gmail_credentials:
        print("⚠️ GMAIL_CREDENTIALS: 未設定")
    else:
        try:
            creds_data = json.loads(gmail_credentials)
            client_id = creds_data.get("installed", {}).get("client_id", "N/A")
            print(f"🔑 Client ID: {client_id[:20]}...")
        except Exception:
            print("⚠️ GMAIL_CREDENTIALS: 無効なJSON形式")

    # Check token
    if not gmail_token:
        print("⚠️ GMAIL_TOKEN: 未設定")
        print()
        print("❌ Gmail API: トークンが設定されていません")
        print("   → tests/setup_gmail_oauth.py を実行してトークンを生成してください")
        return False
    else:
        try:
            token_data = json.loads(gmail_token)
            if "refresh_token" in token_data:
                print("🎫 Token: リフレッシュトークンあり")
            else:
                print("⚠️ Token: リフレッシュトークンなし")
        except Exception:
            print("⚠️ GMAIL_TOKEN: 無効なJSON形式")
            return False

    print()

    # Try to authenticate
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_info(
            json.loads(gmail_token),
            scopes=["https://www.googleapis.com/auth/gmail.send"],
        )

        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            creds.refresh(Request())
            print("🔄 トークンをリフレッシュしました")

        # Test API connection
        # Note: getProfile requires gmail.readonly or similar. sending-only scope might fail here.
        try:
            service = build("gmail", "v1", credentials=creds)
            profile = service.users().getProfile(userId="me").execute()
            email = profile.get("emailAddress", "N/A")
            print(f"📧 認証済みメールアドレス: {email}")
        except Exception as e:
            if "insufficient authentication scopes" in str(e):
                print("⚠️ プロファイル取得不可 (権限不足 - gmail.sendのみのため正常)")
                # トークンリフレッシュが成功していれば認証自体はOKとみなす
            else:
                raise e

        print()
        print("✅ Gmail API: 正常 (認証成功)")
        return True

    except Exception as e:
        error_msg = str(e)
        print("❌ Gmail API: エラー")
        print(f"   → {error_msg}")
        return False


if __name__ == "__main__":
    success = check_gmail()
    print()
    print("=" * 50)
    sys.exit(0 if success else 1)
