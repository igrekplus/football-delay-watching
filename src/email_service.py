"""
メール送信サービス

高レベルのメール送信ロジックを担当（GmailClientへ委譲）。
"""

import os
import re
import logging
from pathlib import Path
from typing import List

import markdown

from src.clients.gmail_client import GmailClient
from src.utils.api_stats import ApiStats

logger = logging.getLogger(__name__)

# テンプレートファイルパス
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "email_template.html"


def _load_email_template() -> str:
    """HTMLテンプレートを読み込む"""
    try:
        return TEMPLATE_PATH.read_text(encoding='utf-8')
    except FileNotFoundError:
        logger.warning(f"Email template not found: {TEMPLATE_PATH}")
        # フォールバック: 最小限のテンプレート
        return "<html><body><div>{content}</div></body></html>"


class EmailService:
    """メール送信サービス（Façade）"""
    
    def __init__(self, client: GmailClient = None):
        """
        Args:
            client: GmailClientインスタンス（省略時は新規作成）
        """
        self.client = client or GmailClient()
        self._template = _load_email_template()
    
    def is_available(self) -> bool:
        """メール送信が利用可能かどうか"""
        return self.client.is_available()
    
    def _markdown_to_html(self, md_content: str) -> str:
        """MarkdownをHTMLに変換"""
        # 画像パスをCIDに変換（後で添付画像と紐付け）
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
        
        return self._template.format(content=html_content)
    
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
        # Markdown → HTML
        html_content = self._markdown_to_html(markdown_content)
        
        # GmailClient経由で送信
        return self.client.send_html_message(
            to=to_email,
            subject=subject,
            html_content=html_content,
            inline_images=image_paths
        )


def send_debug_summary(
    report_urls: List[str],
    matches_summary: List[dict],
    quota_info: dict,
    youtube_stats: dict = None,
    is_mock: bool = False,
    is_debug: bool = False
) -> bool:
    """
    デバッグ用サマリをメール送信するヘルパー関数
    
    Args:
        report_urls: 生成されたレポートのURLリスト
        matches_summary: 試合のサマリ情報リスト
        quota_info: API消費状況
        youtube_stats: YouTube API統計
        is_mock: モックモードかどうか
        is_debug: デバッグモードかどうか
        
    Returns:
        送信成功時True
    """
    from config import config
    from src.utils.datetime_util import DateTimeUtil
    
    if not config.GMAIL_ENABLED:
        logger.info("Gmail notification disabled (GMAIL_ENABLED=False)")
        return False
    
    if not config.NOTIFY_EMAIL:
        logger.warning("NOTIFY_EMAIL not set. Skipping email notification.")
        return False
    
    now = DateTimeUtil.now_jst()
    today_str = DateTimeUtil.format_date_str(now)
    time_str = now.strftime('%H:%M:%S')
    
    # モード表示
    mode_label = ""
    if is_mock:
        mode_label = " [MOCK]"
    elif is_debug:
        mode_label = " [DEBUG]"
    
    subject = f"⚽ サッカー観戦ガイド 実行通知 - {today_str}{mode_label}"
    
    # Markdown形式でサマリを作成
    lines = []
    lines.append(f"# 実行完了通知\n")
    lines.append(f"**実行日時**: {today_str} {time_str} JST\n")
    if mode_label:
        lines.append(f"**モード**: {mode_label.strip()}\n")
    lines.append("")
    
    # レポートURL
    lines.append("## 📋 生成レポート\n")
    if report_urls:
        for url in report_urls:
            lines.append(f"- {url}")
    else:
        lines.append("- レポートなし")
    lines.append("")
    
    # 試合サマリ
    lines.append("## ⚽ 試合サマリ\n")
    if matches_summary:
        lines.append("| 試合 | 大会 | キックオフ | ランク |")
        lines.append("|------|------|-----------|--------|")
        for m in matches_summary:
            match_name = f"{m.get('home', '?')} vs {m.get('away', '?')}"
            comp = m.get('competition', '-')
            kickoff = m.get('kickoff', '-')
            rank = m.get('rank', '-')
            lines.append(f"| {match_name} | {comp} | {kickoff} | {rank} |")
    else:
        lines.append("- 対象試合なし")
    lines.append("")
    
    # API消費状況
    lines.append("## 📊 API消費状況\n")
    api_table = ApiStats.format_table()
    lines.append(api_table)
    lines.append("")
    
    # Webリンク
    lines.append("## 🔗 Webサイト\n")
    lines.append("- [観戦ガイド一覧](https://football-delay-watching-a8830.web.app/)")
    lines.append("")
    
    markdown_content = "\n".join(lines)
    
    service = EmailService()
    return service.send_report(
        to_email=config.NOTIFY_EMAIL,
        subject=subject,
        markdown_content=markdown_content,
        image_paths=None
    )
