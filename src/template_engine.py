"""
Jinja2 テンプレートエンジン設定モジュール

レポート生成用のテンプレート環境を提供する。
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# テンプレートディレクトリのパス
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def get_jinja_env() -> Environment:
    """
    Jinja2 環境を取得
    
    Returns:
        設定済みの Jinja2 Environment インスタンス
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def render_template(template_name: str, **context) -> str:
    """
    テンプレートをレンダリング
    
    Args:
        template_name: テンプレートファイル名（例: "report.html"）
        **context: テンプレートに渡す変数
    
    Returns:
        レンダリングされた HTML 文字列
    """
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**context)


def render_test() -> str:
    """
    動作確認用のテストレンダリング
    Flash がこの関数を呼び出して Jinja2 が正常に動作することを確認する
    """
    return render_template("test.html", message="Jinja2 is working!", items=["Home", "Away", "Draw"])
