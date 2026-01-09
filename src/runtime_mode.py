"""
実行モード管理

アプリケーションの実行モードを一元管理。
各サービスはこのモジュールからモードを判定する。
"""

from enum import Enum
import os

class RuntimeMode(Enum):
    """実行モード"""
    PRODUCTION = "production"  # 本番: 実API、全試合処理
    DEBUG = "debug"            # デバッグ: 実API、1試合のみ
    MOCK = "mock"              # モック: ダミーデータ

def get_current_mode() -> RuntimeMode:
    """
    現在の実行モードを取得
    
    環境変数の優先順位:
    1. USE_MOCK_DATA=True → MOCK
    2. DEBUG_MODE=True → DEBUG
    3. それ以外 → PRODUCTION
    """
    use_mock = os.getenv("USE_MOCK_DATA", "True").lower() == "true"
    debug_mode = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    if use_mock:
        return RuntimeMode.MOCK
    elif debug_mode:
        return RuntimeMode.DEBUG
    else:
        return RuntimeMode.PRODUCTION

def is_mock() -> bool:
    """モックモードかどうか"""
    return get_current_mode() == RuntimeMode.MOCK

def is_debug() -> bool:
    """デバッグモードかどうか（実API使用）"""
    return get_current_mode() == RuntimeMode.DEBUG

def is_production() -> bool:
    """本番モードかどうか"""
    return get_current_mode() == RuntimeMode.PRODUCTION

def uses_real_api() -> bool:
    """実APIを使用するかどうか（DEBUG or PRODUCTION）"""
    return get_current_mode() in (RuntimeMode.DEBUG, RuntimeMode.PRODUCTION)
