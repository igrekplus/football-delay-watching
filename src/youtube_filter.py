"""
YouTubePostFilter - YouTube動画のpost-filterを提供するクラス

YouTubeServiceから分離されたフィルタリングロジック。
各検索メソッドで適用するフィルターを選択的に呼び出す設計。
"""

import logging
from typing import List, Dict

from settings.channels import is_trusted_channel, get_channel_info

logger = logging.getLogger(__name__)


class YouTubePostFilter:
    """YouTube動画のpost-filterを提供するクラス"""

    # exclude_highlights() で除外するキーワードルール
    EXCLUDE_RULES = [
        ("match_highlights", ["match highlights", "extended highlights"]),
        ("highlights", ["highlights"]),
        ("full_match", ["full match", "full game", "full replay"]),
        ("live_stream", ["live", "livestream", "watch live", "streaming"]),
        ("matchday", ["matchday"]),
        ("press_conference", ["press conference"]),
        ("reaction", ["reaction"]),
    ]

    def exclude_highlights(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """
        ハイライト/フルマッチ/ライブ配信を除外
        
        Returns:
            {"kept": [...], "removed": [...]}
        """
        kept: List[Dict] = []
        removed: List[Dict] = []

        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            reason = None

            # highlights + vs/v パターン（試合ハイライト）
            if "highlights" in text and (" vs " in text or " v " in text or " vs." in text):
                reason = "match_highlights_vs"
            else:
                for rule_name, keywords in self.EXCLUDE_RULES:
                    if any(kw in text for kw in keywords):
                        reason = rule_name
                        break

            if reason:
                vv = dict(v)
                vv["filter_reason"] = reason
                removed.append(vv)
            else:
                kept.append(v)

        if removed:
            logger.info(f"exclude_highlights: removed {len(removed)} videos")

        return {"kept": kept, "removed": removed}

    def sort_trusted(self, videos: List[Dict]) -> List[Dict]:
        """
        信頼チャンネル優先でソート + バッジ付与
        
        チューニング中は全件出力、信頼チャンネルにはバッジを付与
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
