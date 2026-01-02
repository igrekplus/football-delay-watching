# API-Football 設計

機能要件「試合抽出・選定 (Match)」「固定情報取得 (Facts)」を実現するためのAPI-Football連携設計。

---

## 1. 概要

| 項目 | 値 |
|------|-----|
| サービス | API-Football (RapidAPI) |
| 実装クラス | `ApiFootballClient` |
| 認証 | `X-RapidAPI-Key` ヘッダー |

---

## 2. エンドポイント一覧

| エンドポイント | 用途 | 対応機能 |
|--------------|------|----------|
| `/fixtures` | 試合一覧・基本情報 | Match |
| `/fixtures/lineups` | スタメン・フォーメーション | Facts |
| `/injuries` | 負傷者・出場停止情報 | Facts |
| `/teams/statistics` | チームフォーム（直近5試合） | Facts |
| `/fixtures/headtohead` | 過去の対戦成績 | Facts |
| `/players` | 選手の国籍取得 | Facts |

---

## 3. エンドポイント詳細

### 3.1 /fixtures (日付指定)
- **用途**: 対象日の試合一覧を取得し、試合ID/キックオフ/会場/レフェリーを取得。
- **メソッド**: GET  
- **パラメータ**: `date` (YYYY-MM-DD, JST基準で前日を設定), `league` (39=EPL, 2=CL), `season` (月>=6なら年、以外は年-1)  
- **参照レスポンス項目**:
  - `fixture.id`
  - `fixture.date`
  - `fixture.status.short`
  - `fixture.venue.name`, `fixture.venue.city`
  - `fixture.referee`
  - `teams.home.name`, `teams.away.name`

### 3.2 /fixtures (id指定)
- **用途**: チームIDや追加メタ情報を取得（フォーム・H2H 用の team id）。
- **パラメータ**: `id` (fixture id)
- **参照項目**:
  - `teams.home.id`, `teams.away.id`

### 3.3 /fixtures/lineups
- **用途**: スタメン・ベンチ・フォーメーション、選手ID取得（国籍取得のため）。
- **パラメータ**: `fixture` (fixture id)
- **参照項目**:
  - `team.name`
  - `formation`
  - `startXI[].player.name`, `startXI[].player.id`
  - `substitutes[].player.name`, `substitutes[].player.id`

### 3.4 /injuries
- **用途**: 負傷者・出場停止情報の一覧。
- **パラメータ**: `fixture` (fixture id)
- **参照項目**:
  - `player.name`
  - `team.name`
  - `player.reason`

### 3.5 /teams/statistics
- **用途**: 直近フォーム（W/D/L文字列）。
- **パラメータ**: `team` (team id), `season`, `league` (現状 39 固定)
- **参照項目**:
  - `form`（例 "WDWLW"）

### 3.6 /players
- **用途**: 選手の国籍を取得し、国旗表示に利用。
- **パラメータ**: `id` (player id), `season`
- **参照項目**:
  - `player.name`
  - `player.nationality`

### 3.7 /fixtures/headtohead
- **用途**: 直近対戦成績を集計（勝ち/引分/負けのみ利用）。
- **パラメータ**: `h2h` (`{home_id}-{away_id}`), `last` (例 5)
- **参照項目**:
  - `goals.home`, `goals.away`
  - `teams.home.id`（勝敗判定に使用）

---

## 4. 制限事項

- 非EPLチーム（例：CL出場のアタランタ）のフォーム取得には、そのチームが所属するリーグID指定が必要
- 現状は EPL (league=39) 固定のため、非EPLチームのフォームは空欄になる

---

## 5. データ仕様の特記事項

### 5.1 Injuriesエンドポイントの仕様 (Issue #87)

| 項目 | 内容 |
|------|------|
| 定義 | 「試合に参加しない**可能性のある**選手」をリストアップ |
| Missing Fixture | 確実に不参加 |
| **Questionable** | 出場するかもしれないが不確実 |

> [!NOTE]
> Questionableステータスの選手は、実際にはベンチ入りしているケースがある。
> そのため、**Substitutes（ベンチ）と Injuries/Suspended に同一選手が表示される場合がある**が、これはAPI仕様通りの動作であり、仕様として許容する。

### 5.2 選手名形式の違い

| エンドポイント | 選手名形式 | 例 |
|--------------|-----------|-----|
| `/fixtures/lineups` | フルネーム | `Kai Havertz` |
| `/injuries` | 略称形式 | `K. Havertz` |

> [!NOTE]
> エンドポイントによって返される選手名の形式が異なる。現状は仕様として許容し、表示上の重複除外等は行わない。

---

---

## 7. 運用・保守

### 7.1 クォータ統計の記録
- `ApiFootballClient` は `_fetch` メソッドを通じて `_update_quota` を呼び出し、`ApiStats` と `config.QUOTA_INFO` を更新する。
- レスポンスヘッダー内の `x-ratelimit-requests-remaining` を監視し、キャッシュヒット以外（実リクエスト発生時）に統計を記録する。
- 低レベルクライアントの `RequestsHttpClient` は、レスポンスヘッダーを `HttpResponse` オブジェクトに正しく引き渡す責務を持つ（Issue #104 で修正済み）。

