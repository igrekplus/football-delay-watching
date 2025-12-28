"""
YouTubePostFilter - YouTube動画のpost-filterを提供するクラス

YouTubeServiceから分離されたフィルタリングロジック。
各検索カテゴリで適用するフィルターを選択的に組み合わせる設計。
"""

import logging
from typing import List, Dict

from settings.channels import is_trusted_channel, get_channel_info

logger = logging.getLogger(__name__)


class YouTubePostFilter:
    """YouTube動画のpost-filterを提供するクラス"""

    # ========== 個別フィルタメソッド ==========

    def filter_match_highlights(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        試合ハイライトを除外（highlights + vs/v パターン）
        """
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if "highlights" in text and (" vs " in text or " v " in text or " vs." in text):
                vv = dict(v)
                vv["filter_reason"] = "match_highlights"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    def filter_highlights(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        単独ハイライトを除外（highlights, match highlights, extended highlights）
        """
        keywords = ["highlights", "match highlights", "extended highlights"]
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if any(kw in text for kw in keywords):
                vv = dict(v)
                vv["filter_reason"] = "highlights"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    def filter_full_match(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        フルマッチを除外（full match, full game, full replay）
        """
        keywords = ["full match", "full game", "full replay"]
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if any(kw in text for kw in keywords):
                vv = dict(v)
                vv["filter_reason"] = "full_match"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    def filter_live_stream(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        ライブ配信を除外（live, livestream, watch live, streaming）
        """
        keywords = ["live", "livestream", "watch live", "streaming"]
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if any(kw in text for kw in keywords):
                vv = dict(v)
                vv["filter_reason"] = "live_stream"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    def filter_press_conference(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        記者会見を除外（press conference）
        """
        keywords = ["press conference"]
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if any(kw in text for kw in keywords):
                vv = dict(v)
                vv["filter_reason"] = "press_conference"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    def filter_reaction(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        リアクション動画を除外（reaction）
        """
        keywords = ["reaction"]
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if any(kw in text for kw in keywords):
                vv = dict(v)
                vv["filter_reason"] = "reaction"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    # ========== 組み合わせAPI ==========

    def apply_filters(self, videos: List[Dict], filters: List[str]) -> Dict[str, List[Dict]]:
        """
        複数フィルタをまとめて適用

        Args:
            videos: 動画リスト
            filters: 適用するフィルタ名のリスト
                     例: ["match_highlights", "highlights", "full_match", "live_stream", "reaction"]

        Returns:
            {"kept": [...], "removed": [...]}
        """
        filter_methods = {
            "match_highlights": self.filter_match_highlights,
            "highlights": self.filter_highlights,
            "full_match": self.filter_full_match,
            "live_stream": self.filter_live_stream,
            "press_conference": self.filter_press_conference,
            "reaction": self.filter_reaction,
        }

        all_removed = []
        current = videos

        for filter_name in filters:
            if filter_name in filter_methods:
                result = filter_methods[filter_name](current)
                current = result["kept"]
                all_removed.extend(result["removed"])

        if all_removed:
            logger.info(f"apply_filters: removed {len(all_removed)} videos")

        return {"kept": current, "removed": all_removed}

    # ========== 後方互換性: 旧メソッド ==========

    def exclude_highlights(self, videos: List[Dict], skip_rules: List[str] = None) -> Dict[str, List[Dict]]:
        """
        [後方互換] ハイライト/フルマッチ/ライブ配信を除外
        
        新しいコードでは apply_filters() を使用してください。
        """
        # 全フィルタのリスト（skip_rulesで除外するもの以外）
        all_filters = ["match_highlights", "highlights", "full_match", "live_stream", "press_conference", "reaction"]
        if skip_rules:
            all_filters = [f for f in all_filters if f not in skip_rules]
        return self.apply_filters(videos, all_filters)

    # ========== その他のフィルタ ==========

    def sort_trusted(self, videos: List[Dict]) -> List[Dict]:
        """
        信頼チャンネル優先でソート + バッジ付与
        """
        for v in videos:
            channel_id = v.get("channel_id", "")
            v["is_trusted"] = is_trusted_channel(channel_id)

            if v["is_trusted"]:
                info = get_channel_info(channel_id)
                v["channel_display"] = f"✅ {info['name']}"
            else:
                v["channel_display"] = f"⚠️ {v.get('channel_name', 'Unknown')}"

        # ソート: 信頼チャンネル優先、その中ではrelevance順維持
        videos.sort(key=lambda v: (
            0 if v["is_trusted"] else 1,
            v.get("original_index", 0)
        ))

        return videos

    def deduplicate(self, videos: List[Dict]) -> List[Dict]:
        """
        重複排除（video_id ベース）
        """
        seen = set()
        unique = []
        for v in videos:
            video_id = v.get("video_id")
            if video_id and video_id not in seen:
                seen.add(video_id)
                unique.append(v)

        if len(videos) != len(unique):
            logger.info(f"deduplicate: removed {len(videos) - len(unique)} duplicates")

        return unique
