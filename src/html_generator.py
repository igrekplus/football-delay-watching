"""
HTML生成モジュール

Markdownレポートを認証付きHTMLに変換してpublic/に配置する。
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path

import pytz
import markdown

from config import config

logger = logging.getLogger(__name__)


def generate_html_report(markdown_content: str, output_dir: str = "public") -> str:
    """
    MarkdownレポートをHTMLに変換してpublic/report.htmlに保存
    
    Args:
        markdown_content: Markdown形式のレポート内容
        output_dir: 出力ディレクトリ（デフォルト: public）
    
    Returns:
        生成されたHTMLファイルのパス
    """
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
    <title>サッカー観戦ガイド レポート</title>
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
    </style>
</head>
<body>
    <div class="container">
        {html_body}
        <div class="timestamp">
            生成日時: {datetime.now(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M JST')}
        </div>
    </div>
</body>
</html>
"""
    
    # 出力ディレクトリ作成
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # ファイル保存
    output_path = os.path.join(output_dir, "report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    logger.info(f"Generated HTML report: {output_path}")
    return output_path


def generate_from_latest_report(reports_dir: str = None, output_dir: str = "public") -> str:
    """
    最新のMarkdownレポートを読み込んでHTMLに変換
    
    Args:
        reports_dir: レポートディレクトリ（デフォルト: config.OUTPUT_DIR）
        output_dir: 出力ディレクトリ
    
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
    
    return generate_html_report(markdown_content, output_dir)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # デバッグモードで実行
    if len(sys.argv) > 1:
        # 引数でMarkdownファイルを指定
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            content = f.read()
        path = generate_html_report(content)
    else:
        # 最新レポートを変換
        path = generate_from_latest_report()
    
    if path:
        print(f"✅ Generated: {path}")
        print(f"Run 'firebase deploy --only hosting' to publish")
    else:
        print("❌ No report found")
