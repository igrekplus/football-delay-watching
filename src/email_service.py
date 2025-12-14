"""
Gmail API を使用してレポートをメール送信するサービス

使用方法:
1. GCP Consoleで Gmail API を有効化
2. OAuth 2.0 クライアントIDを作成（デスクトップアプリ）
3. tests/setup_gmail_oauth.py を実行して初回認証
4. 生成されたトークンを環境変数に設定
"""

import os
import base64
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import List, Optional
from pathlib import Path

import markdown
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# メール用HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a73e8;
            border-bottom: 2px solid #1a73e8;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34a853;
            margin-top: 30px;
        }}
        h3 {{
            color: #5f6368;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 5px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}
        code {{
            background-color: #f1f3f4;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f1f3f4;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""


class EmailService:
    """Gmail APIを使用してメールを送信するサービス"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    def __init__(self):
        """
        環境変数からGmail認証情報を読み込む
        
        Required env vars:
        - GMAIL_CREDENTIALS: OAuth クライアント情報 (JSON string)
        - GMAIL_TOKEN: リフレッシュトークン (JSON string)
        """
        self.credentials = None
        self._init_credentials()
    
    def _init_credentials(self):
        """OAuth2認証情報を初期化"""
        token_json = os.getenv('GMAIL_TOKEN')
        credentials_json = os.getenv('GMAIL_CREDENTIALS')
        
        if not token_json:
            logger.warning("GMAIL_TOKEN not set. Email sending disabled.")
            return
        
        try:
            token_data = json.loads(token_json)
            self.credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            
            # トークンが期限切れの場合、リフレッシュ
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                logger.info("Refreshing expired Gmail token...")
                self.credentials.refresh(Request())
                logger.info("Gmail token refreshed successfully.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Gmail credentials: {e}")
            self.credentials = None
    
    def is_available(self) -> bool:
        """メール送信が利用可能かどうか"""
        return self.credentials is not None and self.credentials.valid
    
    def _markdown_to_html(self, md_content: str) -> str:
        """MarkdownをHTMLに変換"""
        # 画像パスをCIDに変換（後で添付画像と紐付け）
        # ![alt](path) -> ![alt](cid:filename)
        import re
        
        def replace_image_path(match):
            alt = match.group(1)
            path = match.group(2)
            filename = Path(path).name
            return f'![{alt}](cid:{filename})'
        
        md_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image_path, md_content)
        
        # Markdown → HTML変換
        html_content = markdown.markdown(
            md_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        
        return HTML_TEMPLATE.format(content=html_content)
    
    def _create_message_with_attachments(
        self,
        to: str,
        subject: str,
        html_content: str,
        image_paths: List[str] = None
    ) -> dict:
        """画像添付付きのメールメッセージを作成"""
        
        message = MIMEMultipart('related')
        message['To'] = to
        message['Subject'] = subject
        
        # HTML本文
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # 画像を添付（inline）
        if image_paths:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    try:
                        with open(img_path, 'rb') as f:
                            img_data = f.read()
                        
                        filename = Path(img_path).name
                        img_part = MIMEImage(img_data)
                        img_part.add_header('Content-ID', f'<{filename}>')
                        img_part.add_header('Content-Disposition', 'inline', filename=filename)
                        message.attach(img_part)
                        logger.info(f"Attached image: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to attach image {img_path}: {e}")
        
        # Base64エンコード
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}
    
    def send_report(
        self,
        to_email: str,
        subject: str,
        markdown_content: str,
        image_paths: List[str] = None
    ) -> bool:
        """
        レポートをメール送信
        
        Args:
            to_email: 送信先メールアドレス
            subject: メール件名
            markdown_content: Markdown形式のレポート内容
            image_paths: 添付する画像ファイルのパスリスト
            
        Returns:
            送信成功時True
        """
        if not self.is_available():
            logger.error("Gmail credentials not available. Skipping email.")
            return False
        
        try:
            # Markdown → HTML
            html_content = self._markdown_to_html(markdown_content)
            
            # メッセージ作成
            message = self._create_message_with_attachments(
                to_email, subject, html_content, image_paths
            )
            
            # Gmail API でsend
            service = build('gmail', 'v1', credentials=self.credentials)
            result = service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully! Message ID: {result.get('id')}")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


def send_daily_report(report_content: str, image_paths: List[str] = None) -> bool:
    """
    デイリーレポートをメール送信するヘルパー関数
    
    Args:
        report_content: Markdown形式のレポート内容
        image_paths: 添付画像のパスリスト
        
    Returns:
        送信成功時True
    """
    from config import config
    from datetime import datetime
    import pytz
    
    if not config.GMAIL_ENABLED:
        logger.info("Gmail notification disabled (GMAIL_ENABLED=False)")
        return False
    
    if not config.NOTIFY_EMAIL:
        logger.warning("NOTIFY_EMAIL not set. Skipping email notification.")
        return False
    
    # 件名に日付を含める
    jst = pytz.timezone('Asia/Tokyo')
    today_str = datetime.now(jst).strftime('%Y-%m-%d')
    subject = f"⚽ サッカー観戦ガイド - {today_str}"
    
    service = EmailService()
    return service.send_report(
        to_email=config.NOTIFY_EMAIL,
        subject=subject,
        markdown_content=report_content,
        image_paths=image_paths
    )
