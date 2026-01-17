"""
Gmail API クライアント

OAuth2認証とメール送信の低レベル処理を担当。
"""

import base64
import json
import logging
import os
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail APIの低レベルクライアント"""

    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    def __init__(self):
        """
        環境変数からGmail認証情報を読み込む

        Required env vars:
        - GMAIL_TOKEN: リフレッシュトークン (JSON string)
        """
        self.credentials = None
        self._init_credentials()

    def _init_credentials(self):
        """OAuth2認証情報を初期化"""
        token_json = os.getenv("GMAIL_TOKEN")

        if not token_json:
            logger.warning("GMAIL_TOKEN not set. Email sending disabled.")
            return

        try:
            token_data = json.loads(token_json)
            self.credentials = Credentials.from_authorized_user_info(
                token_data, self.SCOPES
            )

            # トークンが期限切れの場合、リフレッシュ
            if (
                self.credentials
                and self.credentials.expired
                and self.credentials.refresh_token
            ):
                logger.info("Refreshing expired Gmail token...")
                self.credentials.refresh(Request())
                logger.info("Gmail token refreshed successfully.")

        except Exception as e:
            logger.error(f"Failed to initialize Gmail credentials: {e}")
            self.credentials = None

    def is_available(self) -> bool:
        """メール送信が利用可能かどうか"""
        return self.credentials is not None and self.credentials.valid

    def send_html_message(
        self, to: str, subject: str, html_content: str, inline_images: list[str] = None
    ) -> bool:
        """
        HTML形式のメールを送信

        Args:
            to: 送信先メールアドレス
            subject: メール件名
            html_content: HTML形式の本文
            inline_images: インライン添付する画像ファイルのパスリスト

        Returns:
            送信成功時True
        """
        if not self.is_available():
            logger.error("Gmail credentials not available. Skipping email.")
            return False

        try:
            # MIMEメッセージ作成
            message = self._create_mime_message(
                to, subject, html_content, inline_images
            )

            # Gmail API でsend
            service = build("gmail", "v1", credentials=self.credentials)
            result = (
                service.users().messages().send(userId="me", body=message).execute()
            )

            logger.info(f"Email sent successfully! Message ID: {result.get('id')}")
            ApiStats.record_call("Gmail API")
            return True

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _create_mime_message(
        self, to: str, subject: str, html_content: str, image_paths: list[str] = None
    ) -> dict:
        """MIMEメッセージを作成してBase64エンコード"""

        message = MIMEMultipart("related")
        message["To"] = to
        message["Subject"] = subject

        # HTML本文
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        # 画像を添付（inline）
        if image_paths:
            for img_path in image_paths:
                if os.path.exists(img_path):
                    try:
                        with open(img_path, "rb") as f:
                            img_data = f.read()

                        filename = Path(img_path).name
                        img_part = MIMEImage(img_data)
                        img_part.add_header("Content-ID", f"<{filename}>")
                        img_part.add_header(
                            "Content-Disposition", "inline", filename=filename
                        )
                        message.attach(img_part)
                        logger.info(f"Attached image: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to attach image {img_path}: {e}")

        # Base64エンコード
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw_message}
