"""
YouTubePostFilter - YouTube動画のpost-filterを提供するクラス

YouTubeServiceから分離されたフィルタリングロジック。
各検索カテゴリで適用するフィルターを選択的に組み合わせる設計。
"""

import logging

from settings.channels import get_channel_info, is_trusted_channel

logger = logging.getLogger(__name__)


class YouTubePostFilter:
    """YouTube動画のpost-filterを提供するクラス"""

    # ========== 個別フィルタメソッド ==========

    def filter_match_highlights(self, videos: list[dict]) -> dict[str, list[dict]]:
        """
        試合ハイライトを除外（highlights + vs/v パターン）
        """
        kept, removed = [], []
        for v in videos:
            text = f"{v.get('title', '')} {v.get('description', '')}".lower()
            if "highlights" in text and (
                " vs " in text or " v " in text or " vs." in text
            ):
                vv = dict(v)
                vv["filter_reason"] = "match_highlights"
                removed.append(vv)
            else:
                kept.append(v)
        return {"kept": kept, "removed": removed}

    def filter_highlights(self, videos: list[dict]) -> dict[str, list[dict]]:
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

    def filter_full_match(self, videos: list[dict]) -> dict[str, list[dict]]:
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

    def filter_live_stream(self, videos: list[dict]) -> dict[str, list[dict]]:
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

    def filter_press_conference(self, videos: list[dict]) -> dict[str, list[dict]]:
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

    def filter_reaction(self, videos: list[dict]) -> dict[str, list[dict]]:
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

    def apply_filters(
        self, videos: list[dict], filters: list[str]
    ) -> dict[str, list[dict]]:
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

    def exclude_highlights(
        self, videos: list[dict], skip_rules: list[str] = None
    ) -> dict[str, list[dict]]:
        """
        [後方互換] ハイライト/フルマッチ/ライブ配信を除外

        新しいコードでは apply_filters() を使用してください。
        """
        # 全フィルタのリスト（skip_rulesで除外するもの以外）
        all_filters = [
            "match_highlights",
            "highlights",
            "full_match",
            "live_stream",
            "press_conference",
            "reaction",
        ]
        if skip_rules:
            all_filters = [f for f in all_filters if f not in skip_rules]
        return self.apply_filters(videos, all_filters)

    # ========== その他のフィルタ ==========

    def sort_trusted(self, videos: list[dict]) -> list[dict]:
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

        # ソート: 信頼チャンネル優先、その中では公開日時が新しい順（降順）
        # 安定ソートを利用して、まず日時で降順ソートし、次に信頼フラグで昇順（0:Trusted, 1:Untrusted）ソートする
        videos.sort(key=lambda v: v.get("published_at", ""), reverse=True)
        videos.sort(key=lambda v: 0 if v["is_trusted"] else 1)

        return videos

    def deduplicate(self, videos: list[dict]) -> list[dict]:
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

    # ========== LLM-based Context Filter (Issue #109) ==========

    def filter_by_context(
        self, videos: list[dict], home_team: str, away_team: str, gemini_client
    ) -> dict[str, list[dict]]:
        """
        Gemini APIを使用してコンテキストベースのフィルタリングを行う。

        指定された2チーム間の直接対決に関連する動画のみを残す。

        Args:
            videos: 動画リスト
            home_team: ホームチーム名
            away_team: アウェイチーム名
            gemini_client: GeminiRestClientインスタンス

        Returns:
            {"kept": [...], "removed": [...]}
        """
        if not videos:
            return {"kept": [], "removed": []}

        # 入力データを構築（最大20件に制限してトークン節約）
        MAX_VIDEOS_FOR_LLM = 20
        candidates = videos[:MAX_VIDEOS_FOR_LLM]

        video_data = []
        for i, v in enumerate(candidates):
            video_data.append(
                {
                    "id": i,
                    "title": v.get("title", ""),
                    "channel": v.get("channel_name", ""),
                }
            )

        import json

        video_json = json.dumps(video_data, ensure_ascii=False)

        prompt = f"""あなたはサッカー動画のフィルタリング担当者です。

以下のYouTube動画リストから、「{home_team}」と「{away_team}」の**直接対決**に関連する動画のみを厳選してください。

## フィルタリングルール (厳格)
- ✅ 残す: **{home_team} と {away_team} の両方が**試合またはトピックの主語になっている動画
- ❌ 完全除外: 片方のチームしか登場しない動画（例: {home_team} vs 別チーム）
- ❌ 完全除外: リーグ全体のまとめや、関係ないチーム同士の試合

## 動画リスト
{video_json}

## 出力形式
以下のJSON形式で回答してください。他のテキストは不要です。
```json
{{"kept_indices": [0, 2, 5], "reasoning": "簡潔な理由"}}
```

kept_indicesには残すべき動画のid（数字）のリストを入れてください。"""

        try:
            response_text = gemini_client.generate_content(prompt).strip()

            # マークダウンコードブロックを除去
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                # 最初と最後の``` を除去
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = "\n".join(lines)

            result = json.loads(response_text)
            kept_indices = set(result.get("kept_indices", []))
            reasoning = result.get("reasoning", "")

            logger.info(
                f"[LLM FILTER] {home_team} vs {away_team}: kept {len(kept_indices)}/{len(candidates)} videos. Reason: {reasoning}"
            )

            kept = []
            removed = []

            for i, v in enumerate(candidates):
                if i in kept_indices:
                    kept.append(v)
                else:
                    vv = dict(v)
                    vv["filter_reason"] = "llm_context_filter"
                    removed.append(vv)

            # MAX_VIDEOS_FOR_LLM を超えた動画はそのまま残す（保守的に）
            if len(videos) > MAX_VIDEOS_FOR_LLM:
                kept.extend(videos[MAX_VIDEOS_FOR_LLM:])

            return {"kept": kept, "removed": removed}

        except json.JSONDecodeError as e:
            logger.warning(f"[LLM FILTER] JSON parse error: {e}. Skipping LLM filter.")
            return {"kept": videos, "removed": []}
        except Exception as e:
            logger.error(f"[LLM FILTER] Error: {e}. Skipping LLM filter.")
            return {"kept": videos, "removed": []}
