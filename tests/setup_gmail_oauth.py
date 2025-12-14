#!/usr/bin/env python3
"""
Gmail API OAuth2 初回認証スクリプト

このスクリプトを実行して、Gmail APIへのアクセス権限を取得します。
生成されたトークンはGitHub Secretsに登録してください。

使用方法:
1. GCP Console で Gmail API を有効化
2. OAuth 2.0 クライアントID（デスクトップアプリ）を作成
3. credentials.json をダウンロードしてこのディレクトリに配置
4. このスクリプトを実行: python tests/setup_gmail_oauth.py
5. ブラウザでGoogleアカウントにログイン
6. 出力されたトークンをGitHub Secretsに登録
"""

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    creds = None
    credentials_file = '.gmail_credentials.json'
    token_file = '.gmail_token.json'
    
    # 既存のトークンがあれば読み込み
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # トークンがないか、無効な場合は新規取得
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                print(f"ERROR: {credentials_file} not found!")
                print("\n手順:")
                print("1. GCP Console -> APIs & Services -> Credentials")
                print("2. Create OAuth 2.0 Client ID (Desktop app)")
                print("3. Download JSON and save as 'credentials.json'")
                return
            
            print("Starting OAuth2 flow...")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # トークンを保存
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
        print(f"\n✅ Token saved to {token_file}")
    
    print("\n" + "="*60)
    print("GitHub Secrets に以下を登録してください:")
    print("="*60)
    
    # GMAIL_TOKEN
    token_data = json.loads(creds.to_json())
    print("\n📌 GMAIL_TOKEN:")
    print("-" * 40)
    print(json.dumps(token_data, indent=2))
    
    # GMAIL_CREDENTIALS (optional, for reference)
    if os.path.exists(credentials_file):
        print("\n📌 GMAIL_CREDENTIALS:")
        print("-" * 40)
        with open(credentials_file, 'r') as f:
            creds_data = json.load(f)
        print(json.dumps(creds_data, indent=2))
    
    print("\n" + "="*60)
    print("登録方法:")
    print("  gh secret set GMAIL_TOKEN < token.json")
    print("  gh secret set GMAIL_CREDENTIALS < credentials.json")
    print("  gh secret set NOTIFY_EMAIL --body 'your-email@gmail.com'")
    print("="*60)

if __name__ == '__main__':
    main()
