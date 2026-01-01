"""
HTML生成モジュール

MarkdownレポートをHTMLに変換してpublic/reports/に配置する。
責務: HTML生成に特化（CSS外部参照、manifest管理はManifestManagerへ委譲）
"""

import os
import logging
from pathlib import Path

import markdown
from typing import Union

from config import config
from src.domain.models import MatchData, MatchAggregate
from src.clients.firebase_sync_client import FirebaseSyncClient
from src.manifest_manager import ManifestManager
from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)

REPORTS_DIR = "public/reports"
CSS_PATH = "/assets/report_styles.css"


def sync_from_firebase() -> int:
    """
    Firebase Hostingから既存のHTMLファイルをダウンロードしてローカルに保存
    デプロイ前に実行することでファイル消失を防ぐ
    
    Returns:
        ダウンロードしたファイル数
    """
    client = FirebaseSyncClient()
    return client.sync_reports(Path(REPORTS_DIR))


def generate_html_report(markdown_content: str, report_datetime: str = None) -> str:
    """
    MarkdownレポートをHTMLに変換してpublic/reports/に日時付きで保存
    
    Args:
        markdown_content: Markdown形式のレポート内容
        report_datetime: レポート日時 (YYYY-MM-DD_HHMMSS形式、省略時は現在日時)
    
    Returns:
        生成されたHTMLファイルのパス
    """
    now_jst = DateTimeUtil.now_jst()
    
    if report_datetime is None:
        report_datetime = now_jst.strftime('%Y-%m-%d_%H%M%S')
    
    # 表示用（日付部分を抽出）
    report_date = report_datetime.split('_')[0] if '_' in report_datetime else report_datetime
    timestamp = DateTimeUtil.format_display_timestamp(now_jst)
    
    # デバッグ/モックモード判定（タイトル表示用）
    if config.USE_MOCK_DATA:
        mode_prefix = "[MOCK] "
        mode_banner = '<div class="mode-banner mode-banner-mock">🧪 MOCK MODE - このレポートはモックデータです</div>'
    elif config.DEBUG_MODE:
        mode_prefix = "[DEBUG] "
        mode_banner = '<div class="mode-banner mode-banner-debug">🔧 DEBUG MODE - このレポートはデバッグ用です</div>'
    else:
        mode_prefix = ""
        mode_banner = ""
    
    # Markdown→HTML変換
    html_body = markdown.markdown(
        markdown_content,
        extensions=['tables', 'fenced_code', 'nl2br']
    )
    
    # CSS外部参照HTMLテンプレート
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{mode_prefix}サッカー観戦ガイド - {report_date}</title>
    <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← レポート一覧に戻る</a>
        {mode_banner}
        {html_body}
        <div class="timestamp">
            生成日時: {timestamp}
        </div>
    </div>
</body>
</html>
"""
    
    # 出力ディレクトリ作成
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    
    # 日時付きファイル名で保存
    filename = f"report_{report_datetime}.html"
    output_path = os.path.join(REPORTS_DIR, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    logger.info(f"Generated HTML report: {output_path}")
    
    # manifest.json更新
    manifest_manager = ManifestManager()
    manifest_manager.load_with_remote_merge()
    manifest_manager.add_legacy_report(report_datetime, filename, timestamp)
    manifest_manager.deduplicate_legacy_reports()
    manifest_manager.save()
    
    return output_path


def generate_html_reports(report_list: list) -> list:
    """
    試合別レポートを複数HTMLファイルとして生成（新方式）
    
    Args:
        report_list: ReportGenerator.generate_all()の戻り値
            [{
                "match": Union[MatchData, MatchAggregate],
                "markdown_content": str,
                "image_paths": List[str],
                "filename": str  # "2025-12-27_ManchesterCity_vs_Arsenal_20251228_072100"
            }, ...]
    
    Returns:
        生成されたHTMLファイルパスのリスト
    """
    now_jst = DateTimeUtil.now_jst()
    timestamp = DateTimeUtil.format_display_timestamp(now_jst)
    generation_datetime = DateTimeUtil.format_filename_datetime(now_jst)
    
    # デバッグ/モックモード判定
    if config.USE_MOCK_DATA:
        mode_prefix = "[MOCK] "
        mode_banner = '<div class="mode-banner mode-banner-mock">🧪 MOCK MODE - このレポートはモックデータです</div>'
    elif config.DEBUG_MODE:
        mode_prefix = "[DEBUG] "
        mode_banner = '<div class="mode-banner mode-banner-debug">🔧 DEBUG MODE - このレポートはデバッグ用です</div>'
    else:
        mode_prefix = ""
        mode_banner = ""
    
    # 出力ディレクトリ作成
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    
    html_paths = []
    match_entries = []  # manifest用のエントリ
    
    for report in report_list:
        match = report["match"]
        markdown_content = report["markdown_content"]
        filename_base = report["filename"]
        
        # Markdown→HTML変換
        html_body = markdown.markdown(
            markdown_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
        
        # ページタイトル（実行時刻を含む）
        time_part = generation_datetime.split('_')[1]  # "HHMMSS"
        time_display = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"
        title = f"{mode_prefix}{match.home_team} vs {match.away_team} - {match.competition} ({time_display})"
        
        # CSS外部参照HTMLテンプレート
        html_template = _get_html_template(title, html_body, timestamp, mode_banner)
        
        # HTMLファイル保存
        html_filename = f"{filename_base}.html"
        output_path = os.path.join(REPORTS_DIR, html_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        
        html_paths.append(output_path)
        logger.info(f"Generated HTML: {output_path}")
        
        # manifest用エントリ
        match_entries.append({
            "fixture_id": match.id,
            "home_team": match.home_team,
            "away_team": match.away_team,
            "competition": match.competition,
            "kickoff_local": match.kickoff_local,
            "kickoff_jst": match.kickoff_jst,
            "file": html_filename,
            "match_date": match.match_date_local,
            "is_mock": config.USE_MOCK_DATA,
            "is_debug": config.DEBUG_MODE
        })
    
    # manifest更新（日付グループ構造）
    manifest_manager = ManifestManager()
    manifest_manager.load_with_remote_merge()
    manifest_manager.add_match_entries(match_entries, generation_datetime)
    manifest_manager.migrate_legacy_reports()
    manifest_manager.save()
    
    return html_paths


def _get_html_template(title: str, html_body: str, timestamp: str, mode_banner: str = "") -> str:
    """HTMLテンプレートを生成（CSS外部参照）"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← レポート一覧に戻る</a>
        {mode_banner}
        {html_body}
        <div class="timestamp">
            生成日時: {timestamp}
        </div>
    </div>
</body>
</html>
"""


def generate_from_latest_report(reports_dir: str = None) -> str:
    """
    最新のMarkdownレポートを読み込んでHTMLに変換
    
    Args:
        reports_dir: レポートディレクトリ（デフォルト: config.OUTPUT_DIR）
    
    Returns:
        生成されたHTMLファイルのパス
    """
    import glob
    
    if reports_dir is None:
        reports_dir = config.OUTPUT_DIR
    
    # 最新のMarkdownファイルを探す
    md_files = glob.glob(os.path.join(reports_dir, "*.md"))
    if not md_files:
        logger.warning(f"No markdown files found in {reports_dir}")
        return None
    
    # 最新ファイルを取得（更新日時順）
    latest_file = max(md_files, key=os.path.getmtime)
    
    with open(latest_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # ファイル名から日時を抽出（可能であれば）
    basename = os.path.basename(latest_file).replace(".md", "")
    
    return generate_html_report(content, basename)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            content = f.read()
        path = generate_html_report(content)
    else:
        path = generate_from_latest_report()
    
    if path:
        print(f"✅ Generated: {path}")
        print(f"Run 'firebase deploy --only hosting' to publish")
    else:
        print("❌ No report found")
