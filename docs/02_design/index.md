# 設計書

本ドキュメントは、機能要件 ([01_requirements/index.md](../01_requirements/index.md)) を実現するための設計を記述する。

---

## 設計ドキュメント一覧

| ドキュメント | 概要 | 対応機能 |
|-------------|------|----------|
| [system_overview.md](./system_overview.md) | システム全体設計・アーキテクチャ構成図 | 全体 |
| [implementation_flow.md](./implementation_flow.md) | 実装フロー・責務境界・データフロー | 全体 |
| [external_apis.md](./external_apis.md) | 外部API連携設計（概要・リンク集） | 全体 |
| [api_football_design.md](./api_football_design.md) | API-Football設計・エンドポイント詳細 | Match, Facts |
| [cache_design.md](./cache_design.md) | キャッシュ設計（GCS, TTL） | Match, Facts, YouTube |
| [login_design.md](./login_design.md) | ログイン・認証設計（Firebase Auth） | Delivery |
| [llm_constraints.md](./llm_constraints.md) | LLM制約仕様（入力条件・禁止事項・失敗時挙動） | News |
| [data_model.md](./data_model.md) | データモデル設計・責務境界・生成物スキーマ | 全体 |
| [domain_models.md](./domain_models.md) | ドメインモデル設計（MatchData） | 全体 |
| [youtube_search_design.md](./youtube_search_design.md) | YouTube検索設計（カテゴリ・フィルタ・ソート） | YouTube |
| [news_search_design.md](./news_search_design.md) | ニュース検索設計（Google Custom Search） | News |
| [common_utilities.md](./common_utilities.md) | 共通ユーティリティ設計（DateTimeUtil, http_utils） | 全体 |

> **Note**: 運用関連ドキュメントは [03_operations/](../03_operations/) を参照。

---

## アーキテクチャ概要

```mermaid
graph TD
    A[GitHub Actions 07:00 JST] --> B[main.py]
    B --> C[MatchProcessor]
    C --> D[FactsService]
    D --> E[NewsService]
    E --> F[YouTubeService]
    F --> G[ReportGenerator]
    G --> H[HtmlGenerator]
    H --> I[EmailService]
    
    C -.-> J[(API-Football)]
    D -.-> J
    E -.-> K[(Google Search)]
    E -.-> L[(Gemini API)]
    F -.-> M[(YouTube API)]
    I -.-> N[(Gmail API)]
    
    subgraph Cache
        O[(GCS Cache)]
    end
    J -.-> O
    M -.-> O
```

---

## 技術スタック

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| 言語 | Python 3.11 | アプリケーション |
| 実行基盤 | GitHub Actions | スケジュール実行 |
| キャッシュ | Google Cloud Storage | APIレスポンスキャッシュ |
| ホスティング | Firebase Hosting | レポート配信 |
| 認証 | Firebase Auth | ログイン機能 |

---

## 環境変数

詳細はローカル開発環境の `.env` および GitHub Secrets に設定する。

| サービス | 環境変数名 | 用途 |
|----------|-----------|------|
| API-Football | `RAPIDAPI_KEY` | 試合データ取得 |
| Gemini API | `GOOGLE_API_KEY` | AI要約・検閲 |
| Google Search | `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID` | 記事検索 |
| Gmail API | `GMAIL_TOKEN`, `GMAIL_CREDENTIALS` | メール送信認証 |
| メール設定 | `NOTIFY_EMAIL`, `GMAIL_ENABLED` | 送信先・有効化 |
