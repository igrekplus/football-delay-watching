#!/usr/bin/env python3
"""
Gmail API 送信テストスクリプト

メール送信機能が正常に動作するかテストします。

使用方法:
  環境変数を設定してから実行:

  export GMAIL_TOKEN='{"token": "...", ...}'
  export NOTIFY_EMAIL='your-email@gmail.com'
  export GMAIL_ENABLED='True'
  python tests/verify_gmail.py
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import logging

from src.email_service import EmailService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    print("=" * 60)
    print("Gmail API テスト")
    print("=" * 60)

    # 環境変数チェック
    gmail_token = os.getenv("GMAIL_TOKEN")
    notify_email = os.getenv("NOTIFY_EMAIL")
    gmail_enabled = os.getenv("GMAIL_ENABLED", "False").lower() == "true"

    print("\n📋 設定状況:")
    print(f"  GMAIL_ENABLED: {gmail_enabled}")
    print(f"  NOTIFY_EMAIL: {notify_email or '(未設定)'}")
    print(f"  GMAIL_TOKEN: {'設定済み' if gmail_token else '(未設定)'}")

    if not gmail_token:
        print("\n❌ GMAIL_TOKEN が設定されていません。")
        print("   tests/setup_gmail_oauth.py を実行してトークンを取得してください。")
        return False

    if not notify_email:
        print("\n❌ NOTIFY_EMAIL が設定されていません。")
        return False

    # EmailService 初期化テスト
    print("\n🔄 EmailService 初期化中...")
    service = EmailService()

    if not service.is_available():
        print("❌ Gmail認証に失敗しました。")
        print("   トークンが期限切れの可能性があります。")
        print("   tests/setup_gmail_oauth.py を再実行してください。")
        return False

    print("✅ Gmail認証成功!")

    # テストメール送信
    print(f"\n📧 テストメール送信中... ({notify_email})")

    test_markdown = """
# テストメール

このメールは **Gmail API** テストです。

## チェックリスト

- [ ] HTMLとして正しく表示される
- [ ] 日本語が文字化けしない
- [ ] スタイルが適用されている

## テスト情報

| 項目 | 値 |
|------|-----|
| 送信元 | Gmail API |
| 形式 | HTML (Markdown変換) |

---

*このメールは football-delay-watching プロジェクトから送信されました。*
"""

    success = service.send_report(
        to_email=notify_email,
        subject="[テスト] Gmail API 送信確認",
        markdown_content=test_markdown,
    )

    if success:
        print("✅ テストメール送信成功!")
        print(f"   {notify_email} の受信箱を確認してください。")
        return True
    else:
        print("❌ テストメール送信失敗")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
