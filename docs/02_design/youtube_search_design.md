# YouTube検索設計

YouTube Data API v3を使用した動画検索の設計。キックオフ前の関連動画を取得し、ネタバレを防止する。

---

## 1. 検索カテゴリ別仕様

### 1.1 検索カテゴリ一覧

| カテゴリ | クエリテンプレート | 検索期間 | 言語 | 最大件数 |
|---------|-------------------|---------|------|---------|
| 記者会見 | `{team} {manager} press conference` | 48時間前〜キックオフ | 英語 | 2/チーム |
| 過去対戦 | `{home} vs {away} highlights` | 730日前〜24時間前 | - | 1 |
| 戦術分析 | `{team} 戦術 分析` | 180日前〜キックオフ | 日本語 | 2/チーム |
| 選手紹介 | `{player} {team} プレー` | 180日前〜キックオフ | 日本語 | 6 |
| 練習風景 | `{team} training` | 168時間前〜キックオフ | 英語 | 2/チーム |

> 実装: [settings/search_specs.py](../../settings/search_specs.py) の `YOUTUBE_SEARCH_SPECS`

### 1.2 検索期間の設計意図

| カテゴリ | 期間 | 設計理由 |
|---------|------|---------|
| 記者会見 | 48時間前 | 試合前会見は通常1-2日前に実施 |
| 過去対戦 | 730日〜24時間前 | 過去2年の対戦を対象、直近24時間は除外（ネタバレ防止） |
| 戦術分析 | 180日前 | シーズン内の戦術解説を網羅 |
| 選手紹介 | 180日前 | 選手のプレー集は長期間有効 |
| 練習風景 | 168時間前 | 1週間以内の直近練習動画 |

### 1.3 言語設定

| 言語 | 対象カテゴリ | API パラメータ |
|------|------------|---------------|
| 英語 | 記者会見, 練習風景 | `relevanceLanguage=en` |
| 日本語 | 戦術分析, 選手紹介 | `relevanceLanguage=ja` |
| 未指定 | 過去対戦 | デフォルト（地域依存） |

---

## 2. 信頼チャンネル設計

YouTube動画の信頼性を判定し、優先表示するための設計。

### 2.1 チャンネルカテゴリ

| カテゴリ | 説明 | 例 |
|---------|------|-----|
| `team` | クラブ公式 | Man City, Liverpool, Arsenal |
| `league` | リーグ公式 | Premier League, UEFA Champions League |
| `broadcaster` | 放送局 | Sky Sports, TNT Sports, BBC |
| `tactics` | 戦術解説 | The Athletic FC, レオザフットボール |

> 実装: [settings/channels.py](../../settings/channels.py) の `TRUSTED_CHANNELS`

### 2.2 優先度ルール

信頼チャンネルフィルターは **post-fetch方式** で動作する:

1. チャンネル指定なしで検索を実行（API効率化）
2. 結果を信頼チャンネル優先でソート
3. バッジを付与して表示

```
ソート順: 信頼チャンネル (is_trusted=True) → 非信頼チャンネル (is_trusted=False)
```

### 2.3 バッジ表示

| 状態 | バッジ | 表示例 |
|------|--------|--------|
| 信頼チャンネル | ✅ | ✅ Liverpool FC |
| 非信頼チャンネル | ⚠️ | ⚠️ FootballHighlightsHD |

> 実装: [src/youtube_filter.py](../../src/youtube_filter.py) の `YouTubePostFilter.sort_trusted()`

---

## 3. YouTubePostFilter設計

YouTube検索結果のフィルタリングを担当するクラスの設計。

### 3.1 除外ルール一覧

| フィルタ名 | 除外対象キーワード | 適用カテゴリ |
|-----------|------------------|-------------|
| `match_highlights` | `highlights` + `vs`/`v` | 記者会見, 戦術分析, 選手紹介, 練習風景 |
| `highlights` | `highlights`, `match highlights`, `extended highlights` | 同上 |
| `full_match` | `full match`, `full game`, `full replay` | 同上 |
| `live_stream` | `live`, `livestream`, `watch live`, `streaming` | 全カテゴリ |
| `press_conference` | `press conference` | 過去対戦, 戦術分析, 選手紹介 |
| `reaction` | `reaction` | 全カテゴリ |

> 実装: [src/youtube_filter.py](../../src/youtube_filter.py) の `YouTubePostFilter`

### 3.2 フィルタ適用フロー

```mermaid
graph LR
    A[API検索結果] --> B[除外フィルタ適用]
    B --> C[信頼チャンネルソート]
    C --> D[重複排除]
    D --> E[件数制限]
    E --> F[最終結果]
```

### 3.3 カテゴリ別適用フィルタ

| カテゴリ | 適用フィルタ |
|---------|-------------|
| 記者会見 | `match_highlights`, `highlights`, `full_match`, `live_stream`, `reaction` |
| 過去対戦 | `live_stream`, `press_conference`, `reaction` |
| 戦術分析 | `match_highlights`, `highlights`, `full_match`, `live_stream`, `press_conference`, `reaction` |
| 選手紹介 | `match_highlights`, `highlights`, `full_match`, `live_stream`, `press_conference`, `reaction` |
| 練習風景 | `match_highlights`, `highlights`, `full_match`, `live_stream`, `press_conference`, `reaction` |

### 3.4 フィルタ結果の返却形式

```python
{
    "kept": [...],      # フィルタを通過した動画
    "removed": [...],   # 除外された動画（reason付き）
    "overflow": [...]   # 件数超過で切り捨てた動画
}
```

---

## 4. 件数制限・ソートロジック

YouTube検索結果の件数制限とソート処理の設計。

> 実装: [src/youtube_service.py](../../src/youtube_service.py) の `YouTubeService`

### 4.1 取得件数の設計

| 項目 | 値 | 説明 |
|------|-----|------|
| API取得件数 | 50件 | `FETCH_MAX_RESULTS = 50`（全カテゴリ共通） |
| カテゴリ別表示上限 | 10件 | `MAX_PER_CATEGORY = 10`（フィルタ・ソート後に適用） |

**設計意図**:
- APIからは多めに取得（50件）し、post-fetchフィルタで除外した後も十分な候補を確保
- 最終的にカテゴリ別に10件まで絞り込み、レポートの可読性を維持

### 4.2 処理パイプライン

```mermaid
graph TD
    A[API検索 50件] --> B[除外フィルタ適用]
    B --> C[信頼チャンネルソート①]
    C --> D[結果返却]
    D --> E[2チーム分マージ]
    E --> F[重複排除]
    F --> G[カテゴリ別再グルーピング]
    G --> H[信頼チャンネルソート②]
    H --> I[10件制限]
    I --> J[overflow分離]
```

### 4.3 ソートロジック詳細

#### 4.3.1 信頼チャンネルソート

```python
videos.sort(key=lambda v: (
    0 if v["is_trusted"] else 1,  # 第1キー: 信頼チャンネル優先
    v.get("original_index", 0)     # 第2キー: API返却順（relevance順）維持
))
```

| ソート順 | 優先度 | 説明 |
|---------|-------|------|
| 第1キー | 信頼 > 非信頼 | 信頼チャンネルを上位に |
| 第2キー | original_index | 同一信頼レベル内ではAPI検索結果の順序を維持（relevance順） |

#### 4.3.2 ソート適用タイミング

| タイミング | 対象 | 目的 |
|-----------|------|------|
| ソート① | 各カテゴリ検索直後 | チーム単位で信頼チャンネルを優先 |
| ソート② | 2チーム分マージ後 | カテゴリ全体で再度信頼チャンネルを優先 |

### 4.4 重複排除ロジック

2チーム分の検索結果をマージした後、`video_id` ベースで重複を排除する。

**重複が発生するケース**:
- 両チームに関連する動画（例: 過去対戦ハイライト）
- 複数選手の検索クエリで同一動画がヒット

### 4.5 Overflow処理

件数制限を超えた動画は `overflow` として保持される。

**Overflowの用途**:
- ログ出力でフィルタリング状況を確認
- 将来の「もっと見る」機能への拡張余地

### 4.6 カテゴリ別クエリ数

| カテゴリ | 通常モード | デバッグモード |
|---------|-----------|--------------|
| 記者会見 | 2クエリ（×2チーム） | 同左 |
| 過去対戦 | 1クエリ | 同左 |
| 戦術分析 | 2クエリ（×2チーム） | 同左 |
| 選手紹介 | 6クエリ（3選手×2チーム） | 2クエリ（1選手×2チーム） |
| 練習風景 | 2クエリ（×2チーム） | 同左 |
| **合計** | **13クエリ/試合** | **9クエリ/試合** |

> 選手数は `config.DEBUG_MODE` で制御: 通常3人/チーム、デバッグ1人/チーム

---

## 5. 関連ドキュメント

- [YouTube動画取得要件](../01_requirements/youtube_integration.md) - 機能要件定義
- [外部API連携設計](./external_apis.md) - API概要
- [キャッシュ設計](./cache_design.md) - GCSキャッシュ
