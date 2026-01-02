# コンポーネント設計

各機能コンポーネントの詳細設計を記述する。

---

## コンポーネント一覧

| ドキュメント | 概要 | 対応機能 |
|-------------|------|----------|
| [api_football.md](../03_components/api_football.md) | API-Football設計・エンドポイント詳細 | Match, Facts |
| [cache.md](./cache.md) | キャッシュ設計（GCS, TTL） | Match, Facts, YouTube |
| [youtube_search.md](./youtube_search.md) | YouTube検索設計（カテゴリ・フィルタ・ソート） | YouTube |
| [news_search.md](./news_search.md) | ニュース検索設計（Google Custom Search） | News |
| [login.md](./login.md) | ログイン・認証設計（Firebase Auth） | Delivery |
| [llm_constraints.md](./llm_constraints.md) | LLM制約仕様（入力条件・禁止事項・失敗時挙動） | News |
| [tuning_workflow.md](./tuning_workflow.md) | チューニングワークフロー設計 | 全体 |
| [common_utilities.md](./common_utilities.md) | 共通ユーティリティ設計（DateTimeUtil, http_utils） | 全体 |

---

## 関連ドキュメント

- [02_architecture/](../02_architecture/) - 全体アーキテクチャ
- [04_operations/](../04_operations/) - 運用手順
