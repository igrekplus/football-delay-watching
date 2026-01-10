"""
API統計管理モジュール

すべてのAPI呼び出し統計を一元管理し、レポートやメール通知で使用する。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ApiStatEntry:
    """個別API統計エントリ"""
    name: str
    calls: int = 0
    cache_hits: int = 0
    remaining_quota: Optional[int] = None
    quota_limit: Optional[int] = None
    quota_limit_str: str = ""  # "10,000/日" のような表示用
    console_url: str = ""  # クォータ確認用URL


class ApiStats:
    """
    API呼び出し統計を一元管理するシングルトン
    
    使用例:
        ApiStats.record_call("Gemini API")
        ApiStats.set_quota("API-Football", remaining=7458, limit=7500)
        stats = ApiStats.get_all()
    """
    
    _stats: Dict[str, ApiStatEntry] = {}
    
    # API定義（デフォルト設定）
    API_DEFINITIONS = {
        "API-Football": {
            "quota_limit_str": "7,500/日",
            "console_url": "https://dashboard.api-football.com/"
        },

        "YouTube Data API": {
            "quota_limit_str": "10,000/日",
            "console_url": "https://console.cloud.google.com/apis/dashboard"
        },
        "Gemini API": {
            "quota_limit_str": "~1,500/日",
            "console_url": "https://aistudio.google.com/app/apikey"
        },
        "Gemini Grounding": {
            "quota_limit_str": "課金制",
            "console_url": "https://console.cloud.google.com/billing"
        },
        "Gmail API": {
            "quota_limit_str": "500/日*",
            "console_url": ""
        }
    }
    
    @classmethod
    def _get_or_create(cls, api_name: str) -> ApiStatEntry:
        """APIエントリを取得または作成"""
        if api_name not in cls._stats:
            defaults = cls.API_DEFINITIONS.get(api_name, {})
            cls._stats[api_name] = ApiStatEntry(
                name=api_name,
                quota_limit_str=defaults.get("quota_limit_str", "不明"),
                console_url=defaults.get("console_url", "")
            )
        return cls._stats[api_name]
    
    @classmethod
    def record_call(cls, api_name: str, count: int = 1) -> None:
        """API呼び出しを記録"""
        entry = cls._get_or_create(api_name)
        entry.calls += count
        logger.debug(f"[ApiStats] {api_name}: +{count} call(s), total={entry.calls}")
    
    @classmethod
    def record_cache_hit(cls, api_name: str, count: int = 1) -> None:
        """キャッシュヒットを記録"""
        entry = cls._get_or_create(api_name)
        entry.cache_hits += count
        logger.debug(f"[ApiStats] {api_name}: +{count} cache hit(s), total={entry.cache_hits}")
    
    @classmethod
    def set_quota(cls, api_name: str, remaining: int, limit: int) -> None:
        """クォータ情報を設定"""
        entry = cls._get_or_create(api_name)
        entry.remaining_quota = remaining
        entry.quota_limit = limit
        logger.debug(f"[ApiStats] {api_name}: quota={remaining}/{limit}")
    
    @classmethod
    def get(cls, api_name: str) -> Optional[ApiStatEntry]:
        """特定APIの統計を取得"""
        return cls._stats.get(api_name)
    
    @classmethod
    def get_all(cls) -> Dict[str, ApiStatEntry]:
        """すべてのAPI統計を取得"""
        # 定義順に並べるため、未記録のAPIも含めて返す
        result = {}
        for api_name in cls.API_DEFINITIONS.keys():
            if api_name in cls._stats:
                result[api_name] = cls._stats[api_name]
            # 呼び出しがないAPIは含めない（0表示を避ける）
        
        # 未定義だが記録されたAPIも追加
        for api_name, entry in cls._stats.items():
            if api_name not in result:
                result[api_name] = entry
        
        return result
    
    @classmethod
    def reset(cls) -> None:
        """統計をリセット（テスト用）"""
        cls._stats = {}
        logger.debug("[ApiStats] Reset all stats")
    
    @classmethod
    def format_table(cls, show_all: bool = True) -> str:
        """
        Markdownテーブル形式でAPI統計を出力
        
        Args:
            show_all: すべての定義済みAPIを表示するかどうか
        
        Returns:
            Markdownテーブル文字列
        """
        lines = []
        lines.append("| API | 実行回数 | 残クォータ | 上限 | 確認リンク |")
        lines.append("|-----|---------|----------|------|-----------|")
        
        # 統計データがあるか確認
        has_stats = len(cls._stats) > 0
        
        if not has_stats and not show_all:
            lines.append("| - | モックモード（API未使用） | - | - | - |")
            return "\n".join(lines)
        
        # show_allの場合は定義済み全APIを表示
        if show_all:
            for api_name, defaults in cls.API_DEFINITIONS.items():
                entry = cls._stats.get(api_name)
                
                if entry:
                    # 実行回数
                    if entry.calls > 0:
                        if entry.cache_hits > 0:
                            calls_str = f"{entry.calls} (キャッシュ: {entry.cache_hits})"
                        else:
                            calls_str = str(entry.calls)
                    elif entry.cache_hits > 0:
                        calls_str = f"0 (キャッシュ: {entry.cache_hits})"
                    else:
                        calls_str = "0"
                    
                    # 残クォータ
                    if entry.remaining_quota is not None:
                        remaining_str = f"{entry.remaining_quota:,}"
                    else:
                        remaining_str = "不明"
                else:
                    calls_str = "0"
                    remaining_str = "不明"
                
                # 上限
                limit_str = defaults.get("quota_limit_str", "不明")
                
                # 確認リンク
                console_url = defaults.get("console_url", "")
                if console_url:
                    link_str = f"[確認]({console_url})"
                else:
                    link_str = "-"
                
                lines.append(f"| {api_name} | {calls_str} | {remaining_str} | {limit_str} | {link_str} |")
        else:
            # 記録されたAPIのみ表示
            for api_name, entry in cls._stats.items():
                if entry.calls > 0:
                    if entry.cache_hits > 0:
                        calls_str = f"{entry.calls} (キャッシュ: {entry.cache_hits})"
                    else:
                        calls_str = str(entry.calls)
                elif entry.cache_hits > 0:
                    calls_str = f"0 (キャッシュ: {entry.cache_hits})"
                else:
                    calls_str = "0"
                
                if entry.remaining_quota is not None:
                    remaining_str = f"{entry.remaining_quota:,}"
                else:
                    remaining_str = "不明"
                
                limit_str = entry.quota_limit_str or "不明"
                
                if entry.console_url:
                    link_str = f"[確認]({entry.console_url})"
                else:
                    link_str = "-"
                
                lines.append(f"| {api_name} | {calls_str} | {remaining_str} | {limit_str} | {link_str} |")
        
        return "\n".join(lines)
