# 外部API連携設計

機能要件「試合抽出・選定 (Match)」「固定情報取得 (Facts)」「ニュース処理 (News)」を実現するための外部API連携設計。

---

## 1. API-Football

機能要件「試合抽出・選定 (Match)」「固定情報取得 (Facts)」を実現する。

### 1.1 概要

| 項目 | 値 |
|------|-----|
| サービス | API-Football (RapidAPI) |
| 実装クラス | `ApiFootballClient` |
| 認証 | `X-RapidAPI-Key` ヘッダー |

### 1.2 エンドポイント

| エンドポイント | 用途 | 対応機能 |
|--------------|------|----------|
| `/fixtures` | 試合一覧・基本情報 | Match |
| `/fixtures/lineups` | スタメン・フォーメーション | Facts |
| `/injuries` | 負傷者・出場停止情報 | Facts |
| `/teams/statistics` | チームフォーム（直近5試合） | Facts |
| `/fixtures/headtohead` | 過去の対戦成績 | Facts |

> 各エンドポイントの詳細パラメータは [api_endpoints.md](./api_endpoints.md) を参照。

### 1.3 制限事項

- 非EPLチーム（例：CL出場のアタランタ）のフォーム取得には、そのチームが所属するリーグID指定が必要
- 現状は EPL (league=39) 固定のため、非EPLチームのフォームは空欄になる

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

## 3. Google Gemini API

機能要件「ニュース処理 (News)」の要約・検閲を実現する。

### 3.1 概要

| 項目 | 値 |
|------|-----|
| サービス | Google Gemini API |
| 実装クラス | `LLMClient` |
| モデル | `gemini-pro-latest` |

### 3.2 役割

| 役割 | 説明 |
|------|------|
| 記事要約 | プレビュー記事を600-1000字に要約 |
| 戦術プレビュー生成 | 戦術分析記事から見どころを抽出 |
| ネタバレ検閲 | 禁止表現を検出・除去 |

### 3.3 モデル選定

| モデル名 | 採用理由 |
|----------|----------|
| `gemini-pro` | 安定動作、十分なクォータ |
| `gemini-1.5-flash` | 次点候補（一部リージョンで404エラー） |
| `gemini-1.5-pro` | 不採用（50 RPD 制限が厳しい） |

---

## 4. YouTube Data API

機能要件「YouTube動画取得 (YouTube)」を実現する。

### 4.1 概要

| 項目 | 値 |
|------|-----|
| サービス | YouTube Data API v3 |
| 実装クラス | `YouTubeService` |
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
