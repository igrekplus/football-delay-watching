# アーキテクチャ設計

本ドキュメントは、機能要件 ([01_requirements/index.md](../01_requirements/index.md)) を実現するための全体設計を記述する。

---

## アーキテクチャドキュメント一覧

| ドキュメント | 概要 |
|-------------|------|
| [system_overview.md](./system_overview.md) | システム全体設計・アーキテクチャ構成図 |
| [implementation_flow.md](./implementation_flow.md) | 実装フロー・責務境界・データフロー |
| [external_apis.md](./external_apis.md) | 外部API連携設計（概要・リンク集） |
| [data_models.md](./data_models.md) | データモデル設計・責務境界・生成物スキーマ |
| [domain_models.md](./domain_models.md) | ドメインモデル設計（MatchAggregate/MatchData） |

> **Note**: コンポーネント設計は [03_components/](../03_components/) を参照。
> 運用関連は [04_operations/](../04_operations/) を参照。

---

## アーキテクチャ概要

```mermaid
graph TD
    A[GitHub Actions] --> B[main.py]
    B --> C[MatchProcessor]
    C --> C1[MatchScheduler + FixtureStatusManager<br/>(prod only)]
    C1 --> C2[MatchSelector]
    C2 --> D[FactsService]
    D --> E[NewsService]
    E --> F[YouTubeService]
    F --> G[ReportGenerator]
    G --> H[HtmlGenerator]
    H --> I[EmailService]
    
    C -.-> J[(API-Football)]
    D -.-> J
    E -.-> L[(Gemini API + Grounding)]
    F -.-> M[(YouTube API)]
    I -.-> N[(Gmail API)]
    
    subgraph Cache
        O[(GCS Cache)]
        P[(Report Status CSV)]
    end
    J -.-> O
    M -.-> O
    C1 -.-> P
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
