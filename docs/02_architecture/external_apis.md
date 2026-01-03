# 外部API連携設計

機能要件「試合抽出・選定 (Match)」「固定情報取得 (Facts)」「ニュース処理 (News)」を実現するための外部API連携設計。

---

## 1. API-Football

機能要件「試合抽出・選定 (Match)」「固定情報取得 (Facts)」を実現する。

> 詳細は [api_football.md](./api_football.md) を参照。

---

## 2. Google Custom Search API

機能要件「ニュース処理 (News)」の記事収集を実現する。

### 2.1 概要

| 項目 | 値 |
|------|-----|
| サービス | Google Custom Search API |
| 実装クラス | `GoogleSearchClient` |
| 認証 | API Key + Search Engine ID |

### 2.2 検索クエリ設計

```
"{チーム名} preview today" -site:bbc.com
```

- `preview` キーワードで試合前記事に絞り込み
- `-site:bbc.com` で結果速報サイトを除外

---

## 3. Google Gemini API (GenAI)

機能要件「ニュース処理」「検閲」「フィルタリング」を実現する。
責務により使用するクライアントと参照すべきドキュメントが異なる。

### 3.1 責務とコンポーネント

| 責務 (Task Category) | 機能 (Task) | クライアント | モデル | 参照ドキュメント |
|---|---|---|---|---|
| **Generation (Standard)** | ニュース要約, 戦術プレビュー | SDK / REST | `gemini-pro-latest` / `gemini-2.0-flash-exp` | [generation.md](../03_components/gemini_tasks/generation.md) |
| **Generation (Grounding)** | インタビュー要約 | REST (`GeminiRestClient`) | `gemini-2.0-flash-exp` | [grounding.md](../03_components/gemini_tasks/grounding.md) |
| **Validation (Safety)** | ネタバレ検閲 | SDK (`google-generativeai`) | `gemini-pro-latest` | [safety.md](../03_components/gemini_tasks/safety.md) |
| **Filtering** | YouTube動画選別 | REST (`GeminiRestClient`) | `gemini-2.0-flash-exp` | [filtering.md](../03_components/gemini_tasks/filtering.md) |

> **共通仕様**: [common.md](../03_components/gemini_tasks/common.md)を参照。

### 3.2 モデル選定基準

| モデル名 | 用途 | 採用理由 |
|----------|------|----------|
| `gemini-2.0-flash-exp` | Grounding, Filtering, Preview | 高速、JSON出力安定、Grounding機能が強力 |
| `gemini-pro` (latest) | 汎用生成, 検閲 | 安定動作、十分なクォータ (RPM) |

---

## 4. YouTube Data API

機能要件「YouTube動画取得 (YouTube)」を実現する。

### 4.1 概要

| 項目 | 値 |
|------|-----|
| サービス | YouTube Data API v3 |
| 実装クラス | `YouTubeSearchClient` (検索・キャッシュ) / `YouTubeService` (ロジック) |
| 認証 | API Key |

### 4.2 詳細

[youtube_integration.md](../01_requirements/youtube_integration.md) を参照。

---

## 5. Gmail API

機能要件「配信 (Delivery)」のメール送信を実現する。

### 5.1 概要

| 項目 | 値 |
|------|-----|
| サービス | Gmail API |
| 実装クラス | `EmailService` |
| 認証 | OAuth2 (リフレッシュトークン) |

### 5.2 機能

- Markdown → HTML 変換（CSSスタイル付き）
- フォーメーション画像のインライン添付
