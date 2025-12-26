"""
HTML生成モジュール

Markdownレポートを認証付きHTMLに変換してpublic/reports/に配置する。
日付付きファイル名で生成し、manifest.jsonでレポート一覧を管理する。
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

import pytz
import markdown

from config import config

logger = logging.getLogger(__name__)

REPORTS_DIR = "public/reports"
MANIFEST_FILE = "public/reports/manifest.json"
FIREBASE_BASE_URL = "https://football-delay-watching-a8830.web.app/reports"


def sync_from_firebase():
    """
    Firebase Hostingから既存のHTMLファイルをダウンロードしてローカルに保存
    デプロイ前に実行することでファイル消失を防ぐ
    """
    import requests
    
    # ディレクトリ作成
    Path(REPORTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(f"{REPORTS_DIR}/images").mkdir(parents=True, exist_ok=True)
    
    # manifest.jsonを取得
    manifest_url = f"{FIREBASE_BASE_URL}/manifest.json?v={datetime.now().timestamp()}"
    try:
        response = requests.get(manifest_url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Could not fetch manifest from Firebase: {response.status_code}")
            return 0
        
        manifest = response.json()
        reports = manifest.get("reports", [])
        
        downloaded = 0
        for report in reports:
            filename = report.get("file")
            if not filename:
                continue
            
            local_path = f"{REPORTS_DIR}/{filename}"
            
            # 既にローカルにある場合はスキップ
            if os.path.exists(local_path):
                continue
            
            # HTMLファイルをダウンロード
            html_url = f"{FIREBASE_BASE_URL}/{filename}"
            try:
                html_response = requests.get(html_url, timeout=30)
                if html_response.status_code == 200:
                    with open(local_path, "w", encoding="utf-8") as f:
                        f.write(html_response.text)
                    logger.info(f"Downloaded from Firebase: {filename}")
                    downloaded += 1
            except Exception as e:
                logger.warning(f"Failed to download {filename}: {e}")
        
        logger.info(f"Synced {downloaded} files from Firebase")
        return downloaded
        
    except Exception as e:
        logger.warning(f"Firebase sync failed: {e}")
        return 0


def generate_html_report(markdown_content: str, report_datetime: str = None) -> str:
    """
    MarkdownレポートをHTMLに変換してpublic/reports/に日時付きで保存
    
    Args:
        markdown_content: Markdown形式のレポート内容
        report_datetime: レポート日時 (YYYY-MM-DD_HHMMSS形式、省略時は現在日時)
    
    Returns:
        生成されたHTMLファイルのパス
    """
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = datetime.now(jst)
    
    if report_datetime is None:
        report_datetime = now_jst.strftime('%Y-%m-%d_%H%M%S')
    
    # 表示用（日付部分を抽出）
    report_date = report_datetime.split('_')[0] if '_' in report_datetime else report_datetime
    timestamp = now_jst.strftime('%Y-%m-%d %H:%M:%S JST')
    
    # デバッグ/モックモード判定（タイトル表示用）
    if config.USE_MOCK_DATA:
        mode_prefix = "[MOCK] "
    elif config.DEBUG_MODE:
        mode_prefix = "[DEBUG] "
    else:
        mode_prefix = ""
    
    # Markdown→HTML変換
    html_body = markdown.markdown(
        markdown_content,
        extensions=['tables', 'fenced_code', 'nl2br']
    )
    
    # CSS付きHTMLテンプレート
    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{mode_prefix}サッカー観戦ガイド - {report_date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
            line-height: 1.8;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 30px 20px;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #74b9ff;
            text-decoration: none;
            font-size: 0.9rem;
        }}
        .back-link:hover {{ text-decoration: underline; }}
        h1, h2, h3 {{
            color: #feca57;
            margin: 25px 0 15px 0;
        }}
        h1 {{ font-size: 2rem; border-bottom: 2px solid #ff6b6b; padding-bottom: 10px; }}
        h2 {{ font-size: 1.5rem; border-left: 4px solid #ff6b6b; padding-left: 15px; }}
        h3 {{ font-size: 1.2rem; color: #74b9ff; }}
        p {{ margin: 10px 0; }}
        ul, ol {{ margin: 15px 0; padding-left: 30px; }}
        li {{ margin: 5px 0; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: rgba(255,255,255,0.05);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }}
        th {{ background: rgba(255,255,255,0.1); color: #feca57; }}
        a {{ color: #74b9ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 10px 0; }}
        code {{ background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; }}
        pre {{ background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px; overflow-x: auto; }}
        .timestamp {{
            text-align: right;
            color: #888;
            font-size: 0.9rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #444;
        }}
        /* Player Card Styles */
        .player-cards {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin: 15px 0;
        }}
        .player-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 12px;
            width: 170px;
            border: 1px solid rgba(255,255,255,0.15);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .player-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        .player-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-size: 0.85rem;
            color: #74b9ff;
            font-weight: bold;
        }}
        .player-card-body {{
            display: flex;
            gap: 10px;
            align-items: flex-start;
        }}
        .player-card-photo {{
            width: 55px;
            height: 55px;
            border-radius: 8px;
            object-fit: cover;
            background: rgba(255,255,255,0.1);
            flex-shrink: 0;
        }}
        .player-card-photo-placeholder {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: #666;
        }}
        .player-card-photo-placeholder::before {{
            content: '👤';
        }}
        .player-card-info {{
            flex: 1;
            min-width: 0;
        }}
        .player-card-name {{
            font-weight: bold;
            color: #feca57;
            font-size: 0.85rem;
            margin-bottom: 2px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .player-card-nationality {{
            color: #aaa;
            font-size: 0.75rem;
        }}
        .player-card-age {{
            color: #888;
            font-size: 0.75rem;
        }}
        /* Injury Card Styles */
        .injury-card {{
            border-color: rgba(255, 107, 107, 0.4);
            background: rgba(255, 107, 107, 0.1);
        }}
        .injury-card .player-card-header {{
            color: #ff6b6b;
        }}
        .injury-reason {{
            color: #ff6b6b;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← レポート一覧に戻る</a>
        {'<div style="background:#9b59b6;color:#fff;padding:10px 15px;border-radius:8px;margin-bottom:20px;font-weight:bold;">🧪 MOCK MODE - このレポートはモックデータです</div>' if config.USE_MOCK_DATA else ('<div style="background:#ff6b6b;color:#fff;padding:10px 15px;border-radius:8px;margin-bottom:20px;font-weight:bold;">🔧 DEBUG MODE - このレポートはデバッグ用です</div>' if config.DEBUG_MODE else '')}
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
    update_manifest(report_datetime, filename, timestamp)
    
    return output_path


def update_manifest(report_datetime: str, filename: str, timestamp: str):
    """
    manifest.jsonを更新してレポート一覧を管理
    Firebase上の既存manifestを取得してマージすることで過去レポートを保持
    """
    import requests
    
    manifest_path = Path(MANIFEST_FILE)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Firebase上の既存manifestを取得（過去レポートを保持するため）
    firebase_url = "https://football-delay-watching-a8830.web.app/reports/manifest.json"
    existing_reports = []
    
    try:
        response = requests.get(firebase_url, timeout=10)
        if response.status_code == 200:
            firebase_manifest = response.json()
            existing_reports = firebase_manifest.get("reports", [])
            logger.info(f"Fetched {len(existing_reports)} existing reports from Firebase")
    except Exception as e:
        logger.warning(f"Could not fetch existing manifest from Firebase: {e}")
    
    # 2. ローカルのmanifestも読み込み（今回のセッションで生成した分）
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            local_manifest = json.load(f)
            local_reports = local_manifest.get("reports", [])
    else:
        local_reports = []
    
    # 3. マージ（既存 + ローカル + 新規）
    all_reports = existing_reports + local_reports
    
    # 新しいレポートを追加（デバッグフラグ付き）
    new_report = {
        "datetime": report_datetime, 
        "file": filename, 
        "generated": timestamp,
        "is_debug": config.DEBUG_MODE,
        "is_mock": config.USE_MOCK_DATA
    }
    all_reports.append(new_report)
    
    # 4. 重複除去（datetimeベース）
    seen = set()
    unique_reports = []
    for r in all_reports:
        dt = r.get("datetime")
        if dt and dt not in seen:
            seen.add(dt)
            unique_reports.append(r)
    
    # 5. 日時でソート（新しい順）
    unique_reports.sort(key=lambda x: x.get("datetime", ""), reverse=True)
    
    # 6. 保存
    manifest = {"reports": unique_reports}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Updated manifest: {len(unique_reports)} reports (merged from Firebase)")


def generate_from_latest_report(reports_dir: str = None) -> str:
    """
    最新のMarkdownレポートを読み込んでHTMLに変換
    
    Args:
        reports_dir: レポートディレクトリ（デフォルト: config.OUTPUT_DIR）
    
    Returns:
        生成されたHTMLファイルのパス
    """
    if reports_dir is None:
        reports_dir = config.OUTPUT_DIR
    
    # 最新のMarkdownファイルを探す
    md_files = list(Path(reports_dir).glob("*.md"))
    if not md_files:
        logger.warning(f"No markdown files found in {reports_dir}")
        return None
    
    # 日付でソートして最新を取得
    latest_file = sorted(md_files, reverse=True)[0]
    logger.info(f"Using latest report: {latest_file}")
    
    # 読み込み
    with open(latest_file, "r", encoding="utf-8") as f:
        markdown_content = f.read()
    
    # 日時はgenerate_html_report内で自動生成
    return generate_html_report(markdown_content)


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
