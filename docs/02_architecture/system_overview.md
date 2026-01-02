# システム全体設計

機能要件 ([01_requirements/index.md](../01_requirements/index.md)) を実現するためのシステム全体設計。

---

## 1. システム概要

サッカーの未視聴試合を、スコアや結果を知ることなく観戦するための「ネタバレ回避観戦ガイド」を自動生成するシステム。

- 実行タイミング：毎日 07:00 (JST)
- 出力形式：HTML（Firebase Hosting）、メール

---

## 2. アーキテクチャ構成

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

## 3. レイヤー構成

| レイヤー | コンポーネント | 詳細設計 |
|---------|---------------|----------|
| データソース | API-Football, Google Search | [external_apis.md](./external_apis.md) |
| AI | Gemini API | [external_apis.md](./external_apis.md) |
| キャッシュ | GCS | [cache.md](./cache.md) |
| 実行基盤 | GitHub Actions | [infrastructure.md](./infrastructure.md) |
| 配信 | Firebase, Gmail | [login.md](./login.md) |

---

## 4. 処理フロー

| ステップ | 処理 | 実装クラス |
|----------|------|-----------|
| 1 | 試合抽出・選定 | `MatchProcessor`, `MatchRanker`, `MatchSelector` |
| 2 | 固定情報取得 | `FactsService` |
| 3 | ニュース処理 | `NewsService` |
| 4 | YouTube動画取得 | `YouTubeService` |
| 5 | レポート生成 | `ReportGenerator` |
| 6 | HTML変換 | `HtmlGenerator` |
| 7 | メール送信 | `EmailService` |
| 8 | キャッシュウォーミング | `CacheWarmer` |

---

## 5. 関連ドキュメント

- [外部API連携設計](./external_apis.md)
- [実行基盤設計](./infrastructure.md)
- [キャッシュ設計](./cache.md)
- [ログイン設計](./login.md)
- [API-Football設計](./api_football.md)
