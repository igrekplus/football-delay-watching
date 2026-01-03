# コンポーネント設計

各機能コンポーネントの詳細設計を記述する。

---

## コンポーネント一覧

| ドキュメント | 概要 | 対応機能 |
|-------------|------|----------|
| [api_football.md](../03_components/api_football.md) | API-Football設計・エンドポイント詳細 | Match, Facts |
| [cache.md](./cache.md) | キャッシュ設計（GCS, TTL） | Match, Facts, YouTube |
| [youtube_search.md](./youtube_search.md) | YouTube検索設計（カテゴリ・フィルタ・ソート） | YouTube |
| [login.md](./login.md) | ログイン・認証設計（Firebase Auth） | Delivery |
| [gemini_tasks/common.md](./gemini_tasks/common.md) | Gemini共通仕様（入力条件・共通制約・禁止事項） | News, Facts |
| [gemini_tasks/generation.md](./gemini_tasks/generation.md) | ニュース要約・戦術プレビュー仕様 (Standard) | News |
| [gemini_tasks/grounding.md](./gemini_tasks/grounding.md) | インタビュー要約仕様 (Grounding) | News |
| [gemini_tasks/safety.md](./gemini_tasks/safety.md) | ネタバレ検閲仕様 (Safety) | News |
| [gemini_tasks/filtering.md](./gemini_tasks/filtering.md) | フィルタリング仕様 (Filtering) | YouTube |
| [gemini_grounding.md](./gemini_grounding.md) | Gemini Grounding機能仕様 | News (Interview) |
| [tuning_workflow.md](./tuning_workflow.md) | チューニングワークフロー設計 | 全体 |
| [common_utilities.md](./common_utilities.md) | 共通ユーティリティ設計（DateTimeUtil, http_utils） | 全体 |

---

## 関連ドキュメント

- [02_architecture/](../02_architecture/) - 全体アーキテクチャ
- [04_operations/](../04_operations/) - 運用手順
