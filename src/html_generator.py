"""
HTML生成モジュール

HTMLレポートをpublic/reports/に配置する。
責務: HTML生成に特化（CSS外部参照、manifest管理はManifestManagerへ委譲）
"""

import logging
import os
from pathlib import Path

import markdown

from config import config
from settings.calendar_data_loader import update_report_link
from src.clients.firebase_sync_client import FirebaseSyncClient
from src.manifest_manager import ManifestManager
from src.utils.datetime_util import DateTimeUtil

logger = logging.getLogger(__name__)

REPORTS_DIR = "public/reports"
CSS_PATH = "../assets/report_styles.css"


def sync_from_firebase() -> int:
    """
    Firebase Hostingから既存のHTMLファイルをダウンロードしてローカルに保存
    デプロイ前に実行することでファイル消失を防ぐ

    Returns:
        ダウンロードしたファイル数
    """
    client = FirebaseSyncClient()
    return client.sync_reports(Path(REPORTS_DIR))


def generate_html_report(content: str, report_datetime: str = None) -> str:
    """
    レポートコンテンツをHTMLファイルとしてpublic/reports/に日時付きで保存

    Args:
        content: HTMLボディ用のレポート内容
        report_datetime: レポート日時 (YYYY-MM-DD_HHMMSS形式、省略時は現在日時)

    Returns:
        生成されたHTMLファイルのパス
    """
    now_jst = DateTimeUtil.now_jst()

    if report_datetime is None:
        report_datetime = DateTimeUtil.format_report_datetime(now_jst)

    # 表示用（日付部分を抽出）
    report_date = (
        report_datetime.split("_")[0] if "_" in report_datetime else report_datetime
    )
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

    # コンテンツをHTMLとして整形
    html_body = markdown.markdown(
        content,
        extensions=["tables", "fenced_code", "nl2br", "markdown.extensions.md_in_html"],
    )

    # CSS外部参照HTMLテンプレート
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{mode_prefix}サッカー観戦ガイド - {report_date}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← レポート一覧に戻る</a>
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
    manifest_manager.save()

    return output_path


def generate_html_reports(report_list: list) -> list:
    """
    試合別レポートを複数HTMLファイルとして生成（新方式）

    Args:
        report_list: ReportGenerator.generate_all()の戻り値
            [{
                "match": MatchAggregate,
                "markdown_content": str,
                "image_paths": List[str],
                "filename": str
            }, ...]

    Returns:
        生成されたHTMLファイルパスのリスト
    """
    now_jst = DateTimeUtil.now_jst()
    DateTimeUtil.format_display_timestamp(now_jst)
    generation_datetime = DateTimeUtil.format_filename_datetime(now_jst)

    # デバッグ/モックモード判定
    if config.USE_MOCK_DATA:
        pass
    elif config.DEBUG_MODE:
        pass
    else:
        pass

    # 出力ディレクトリ作成
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)

    html_paths = []
    match_entries = []  # manifest用のエントリ

    for report in report_list:
        match = report["match"]
        html_content = report["markdown_content"]  # Jinja2 でレンダリング済み
        filename_base = report["filename"]

        # HTMLファイル保存
        html_filename = f"{filename_base}.html"
        output_path = os.path.join(REPORTS_DIR, html_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        html_paths.append(output_path)
        logger.info(f"Generated HTML: {output_path}")

        # manifest用エントリ
        match_entries.append(
            {
                "fixture_id": match.core.id,
                "home_team": match.core.home_team,
                "away_team": match.core.away_team,
                "competition": match.core.competition,
                "kickoff_local": match.core.kickoff_local,
                "kickoff_jst": match.core.kickoff_jst,
                "file": html_filename,
                "match_date": match.core.match_date_local,
                "is_mock": config.USE_MOCK_DATA,
                "is_debug": config.DEBUG_MODE,
            }
        )

        # カレンダーCSVにレポートリンクを記録
        if not config.USE_MOCK_DATA:
            success = update_report_link(
                match.core.id,
                f"/reports/{html_filename}",
                league_name=match.core.competition,
                match_data={
                    "date_jst": match.core.match_date_local,
                    "home_team": match.core.home_team,
                    "away_team": match.core.away_team,
                },
            )
            if not success:
                logger.warning(
                    f"Failed to update calendar report link for fixture {match.core.id}"
                )

    # manifest更新（日付グループ構造）
    manifest_manager = ManifestManager()
    manifest_manager.load_with_remote_merge()
    manifest_manager.add_match_entries(match_entries, generation_datetime)
    manifest_manager.save()

    return html_paths


def _get_html_template(
    title: str, html_body: str, timestamp: str, mode_banner: str = ""
) -> str:
    """HTMLテンプレートを生成（CSS外部参照）"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
    <div class="container">
        <a href="../index.html" class="back-link">← レポート一覧に戻る</a>
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
    最新のレポートを読み込んでHTMLを生成

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

    with open(latest_file, encoding="utf-8") as f:
        content = f.read()

    # ファイル名から日時を抽出（可能であれば）
    basename = os.path.basename(latest_file).replace(".md", "")

    return generate_html_report(content, basename)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            content = f.read()
        path = generate_html_report(content)
    else:
        path = generate_from_latest_report()

    if path:
        print(f"✅ Generated: {path}")
        print("Run 'firebase deploy --only hosting' to publish")
    else:
        print("❌ No report found")
