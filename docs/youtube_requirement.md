# YouTube動画取得ロジック仕様書

## 概要

試合レポートに含めるYouTube動画を取得するロジック。
キックオフ前の動画のみを対象とし、試合結果のネタバレを防ぐ。

---

## APIクォータ情報

| 項目 | 値 |
|------|-----|
| 無料枠 | 10,000ユニット/日 |
| search.list | **100ユニット/リクエスト**（maxResultsに関係なく固定） |
| channels.list | 1ユニット/リクエスト |
| リセット時間 | 太平洋時間 0:00（JST 17:00） |

---

## パラメータ一覧

| パラメータ名 | デフォルト値 | 適用カテゴリ |
|-------------|-------------|--------------|
| `HISTORIC_SEARCH_DAYS` | 730（2年） | カテゴリ1: 過去ハイライト |
| `RECENT_SEARCH_HOURS` | 48 | カテゴリ2: 記者会見, カテゴリ4: 練習風景 |
| `TACTICAL_SEARCH_DAYS` | 180（6ヶ月） | カテゴリ3: 戦術分析, カテゴリ5: 選手紹介 |
| `MAX_RESULTS_PER_CATEGORY` | 3 | 全カテゴリ（最終出力上限）※チューニング中は無制限 |

---

## フィルタリング方式

### 全カテゴリでpost-fetchフィルタ

```
1. API呼び出し: チャンネル指定なし、maxResults=10、order=relevance
2. 取得した動画を信頼チャンネルリストと照合
3. ソート: 信頼チャンネル優先 → relevance順を維持
4. レポート出力: 全件出力（チューニング中）、信頼チャンネルにはバッジ付与
```

### ソートロジック

```python
# ソート順: 信頼チャンネル優先、その中ではrelevance順維持
videos.sort(key=lambda v: (
    0 if v["channel_id"] in TRUSTED_CHANNELS else 1,  # 信頼チャンネル優先
    v["original_index"]  # relevance順を維持
))
```

### レポート出力形式

```markdown
### 🎬 試合前の見どころ動画

| 動画 | チャンネル |
|------|-----------|
| [Tactics Analysis](https://...) | ✅ Tifo Football |
| [Match Preview](https://...) | ⚠️ Unknown Channel |
| [Press Conference](https://...) | ✅ Manchester City |
```

- **✅**: 信頼チャンネル（channels.pyに登録済み）
- **⚠️**: 非信頼チャンネル（要確認、良質なら追加検討）

---

## 動画カテゴリ別仕様

### カテゴリ1: 過去対戦ハイライト (`historic`)

#### 現状

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{home} vs {away} highlights`<br>`{home} {away} extended highlights` | - |
| クエリ数 | **2クエリ/試合** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 730日 | `HISTORIC_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 3 | - |

#### 変更予定 ✅

| 項目 | 変更後 | パラメータ |
|------|--------|-----------|
| 検索クエリ | `{home} vs {away} highlights` のみ | - |
| クエリ数 | **1クエリ/試合** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 730日 | `HISTORIC_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | - |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |
| 削減 | **-100ユニット** | - |

---

### カテゴリ2: 記者会見 (`press_conference`)

#### 現状

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{team} press conference`<br>`{team} 記者会見` | - |
| クエリ数 | 2クエリ × 2チーム = **4クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 48時間 | `RECENT_SEARCH_HOURS` |
| publishedBefore | キックオフ | - |
| maxResults | 2 | - |

#### 変更予定 ✅

| 項目 | 変更後 | パラメータ |
|------|--------|-----------|
| 検索クエリ | `{team} {manager_name} press conference` | - |
| クエリ数 | 1クエリ × 2チーム = **2クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 48時間 | `RECENT_SEARCH_HOURS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | - |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |
| 削減 | **-200ユニット** | - |

---

### カテゴリ3: 戦術分析 (`tactical`)

#### 現状

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{team} tactics analysis` | - |
| クエリ数 | 2クエリ × 戦術チャンネル数 + 選手6名 = **約10クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 180日 | `TACTICAL_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 2 | - |

#### 変更予定 ✅

| 項目 | 変更後 | パラメータ |
|------|--------|-----------|
| 検索クエリ | `{team} 戦術 分析`（日本語のみ） | - |
| クエリ数 | 1クエリ × 2チーム = **2クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 180日 | `TACTICAL_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | - |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |
| 選手検索 | **カテゴリ5へ分離** | - |
| 削減 | **-800ユニット** | - |

---

### カテゴリ4: 練習風景 (`training`)

#### 現状

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{team} training`<br>`{team} 練習` | - |
| クエリ数 | 2クエリ × 2チーム = **4クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 48時間 | `RECENT_SEARCH_HOURS` |
| publishedBefore | キックオフ | - |
| maxResults | 2 | - |

#### 変更予定 ✅

| 項目 | 変更後 | パラメータ |
|------|--------|-----------|
| 検索クエリ | `{team} training` のみ | - |
| クエリ数 | 1クエリ × 2チーム = **2クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 48時間 | `RECENT_SEARCH_HOURS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | - |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |
| 削減 | **-200ユニット** | - |

---

### カテゴリ5: 選手紹介 (`player_highlight`) ← 新規

#### 現状

戦術カテゴリ内で `{player} skills` として検索（6クエリ/試合）

#### 変更予定 ✅

| 項目 | 変更後 | パラメータ |
|------|--------|-----------|
| 検索クエリ | `{player_name}` のみ | - |
| クエリ数 | 3選手 × 2チーム = **6クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 180日 | `TACTICAL_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | - |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |

---

## ログ出力

```
INFO - YouTube result: "Match Preview" by NewChannel (⚠️ not trusted)
INFO - YouTube result: "Tactics Analysis" by TifoFootball_ (✅ trusted)
```

---

## 1試合あたりの総コスト比較

| カテゴリ | 現状クエリ | 変更後クエリ |
|---------|-----------|-------------|
| 過去対戦ハイライト | 2 | 1 |
| 記者会見 | 4 | 2 |
| 戦術分析 | 10 | 2 |
| 練習風景 | 4 | 2 |
| 選手紹介 | (含む) | 6 |
| **合計** | **20** | **13** |
| **コスト** | **2,000** | **1,300** |
| **削減率** | - | **35%削減** |

---

## チャンネル管理（channels.py）

### 変更予定 ✅

チャンネルID + わかりやすい名前 を管理

```python
TRUSTED_CHANNELS = {
    # チャンネルID: (表示名, カテゴリ)
    "UCxxxxx": ("レオザフットボール", "tactics"),
    "UCyyyyy": ("Tifo Football", "tactics"),
    "UCzzzzz": ("Manchester City", "team"),
}
```

---

## タイムゾーン処理

1. `kickoff_jst`をパース → JSTとして設定 → UTCに変換してAPI渡し

---

## 重複排除

動画IDで重複を排除。

---

## キャッシュ

| 項目 | 値 |
|------|-----|
| TTL | 1週間（168時間）※将来的にカテゴリ別TTL検討 |
| 保存先 | `api_cache/youtube/` |
