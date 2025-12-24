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
| `RECENT_SEARCH_HOURS` | 48 | カテゴリ2: 記者会見, カテゴリ5: 練習風景 |
| `TACTICAL_SEARCH_DAYS` | 180（6ヶ月） | カテゴリ3: 戦術分析, カテゴリ4: 選手紹介 |
| `FETCH_MAX_RESULTS` | 10 | 全カテゴリ（API取得件数） |

---

## フィルタリング方式

### post-fetchフィルタ（実装済み）

```
1. API呼び出し: チャンネル指定なし、maxResults=10、order=relevance
2. 取得した動画を信頼チャンネルリスト（TRUSTED_CHANNELS）と照合
3. ソート: 信頼チャンネル優先 → relevance順を維持
4. レポート出力: 全件出力（チューニング中）、信頼チャンネルにはバッジ付与
```

### ソートロジック

```python
# ソート順: 信頼チャンネル優先、その中ではrelevance順維持
videos.sort(key=lambda v: (
    0 if v["is_trusted"] else 1,  # 信頼チャンネル優先
    v["original_index"]  # relevance順を維持
))
```

### レポート出力形式

```markdown
### ■ 📹 試合前の見どころ動画

**🎤 記者会見**

| 動画 | チャンネル |
|------|-----------|
| [Tactics Analysis](https://...) | ✅ Tifo Football |
| [Match Preview](https://...) | ⚠️ Unknown Channel |
| [Press Conference](https://...) | ✅ Manchester City |
```

- **✅**: 信頼チャンネル（channels.py TRUSTED_CHANNELSに登録済み）
- **⚠️**: 非信頼チャンネル（要確認、良質なら追加検討）

---

## 動画カテゴリ別仕様

### カテゴリ1: 過去対戦ハイライト (`historic`)

| 項目 | 値 | パラメータ |
|------|-----|-----------| 
| 検索クエリ | `{home} vs {away} highlights` | - |
| クエリ数 | **1クエリ/試合** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 730日 | `HISTORIC_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | `FETCH_MAX_RESULTS` |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |

---

### カテゴリ2: 記者会見 (`press_conference`)

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{team} {manager_name} press conference` | - |
| クエリ数 | 1クエリ × 2チーム = **2クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 48時間 | `RECENT_SEARCH_HOURS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | `FETCH_MAX_RESULTS` |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |

> **Note**: 監督名はlineups APIの`coach.name`から取得

---

### カテゴリ3: 戦術分析 (`tactical`)

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{team} 戦術 分析`（日本語のみ） | - |
| クエリ数 | 1クエリ × 2チーム = **2クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 180日 | `TACTICAL_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | `FETCH_MAX_RESULTS` |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |

---

### カテゴリ4: 選手紹介 (`player_highlight`)

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{player_name}` のみ | - |
| クエリ数 | 3選手 × 2チーム = **6クエリ**（デバッグ: 2クエリ） | - |
| order | relevance | - |
| publishedAfter | キックオフ - 180日 | `TACTICAL_SEARCH_DAYS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | `FETCH_MAX_RESULTS` |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |

> **Note**: デバッグモード（`DEBUG_MODE=True`）では1選手/チームに削減

---

### カテゴリ5: 練習風景 (`training`)

| 項目 | 値 | パラメータ |
|------|-----|-----------|
| 検索クエリ | `{team} training` のみ | - |
| クエリ数 | 1クエリ × 2チーム = **2クエリ** | - |
| order | relevance | - |
| publishedAfter | キックオフ - 48時間 | `RECENT_SEARCH_HOURS` |
| publishedBefore | キックオフ | - |
| maxResults | 10 | `FETCH_MAX_RESULTS` |
| フィルタ | post-fetch（信頼チャンネル優先ソート） | - |
| 出力 | 全件（チューニング中）、信頼チャンネルにバッジ | - |

---

## ログ出力

```
INFO - YouTube API: 'Manchester City press conference' -> 10 results
INFO - YouTube result: "Pep Guardiola Press Conf..." by Manchester City (✅ trusted)
INFO - YouTube result: "Match Preview" by NewChannel (⚠️ not trusted)
```

---

## 1試合あたりの総コスト

| カテゴリ | クエリ数 | ユニット |
|---------|----------|----------|
| 過去対戦ハイライト | 1 | 100 |
| 記者会見 | 2 | 200 |
| 戦術分析 | 2 | 200 |
| 選手紹介 | 6（デバッグ: 2） | 600（200） |
| 練習風景 | 2 | 200 |
| **合計（通常）** | **13** | **1,300** |
| **合計（デバッグ）** | **9** | **900** |

### 旧仕様との比較

| 項目 | 旧仕様 | 新仕様 | 削減 |
|------|--------|--------|------|
| クエリ数/試合 | 20 | 13 | -35% |
| ユニット/試合 | 2,000 | 1,300 | -700 |

---

## チャンネル管理（channels.py）

### TRUSTED_CHANNELS 構造

```python
TRUSTED_CHANNELS = {
    # チャンネルID: {"name": 表示名, "handle": ハンドル, "category": カテゴリ}
    "UCrRttZIypNTA1Mrfwo745Sg": {
        "name": "Manchester City",
        "handle": "@mancity",
        "category": "team",
    },
    "UCGYlBmk04IsNLTWbRgS-xkQ": {
        "name": "Tifo Football",
        "handle": "@TifoFootball_",
        "category": "tactics",
    },
    # ...
}
```

### ヘルパー関数

- `is_trusted_channel(channel_id)`: 信頼チャンネル判定
- `get_channel_info(channel_id)`: メタデータ取得
- `get_channel_display_name(channel_id, fallback)`: 表示名取得

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
| TTL | 1週間（168時間） |
| 保存先 | `api_cache/youtube/` |

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-12-24 | Issue #27: クエリ削減（20→13）、post-fetchフィルタ方式実装 |
| 2025-12-24 | キャッシュTTL 24時間→1週間に変更 |
| 2025-12-24 | 選手紹介カテゴリを戦術から分離 |
| 2025-12-24 | デバッグモード対応（選手検索1人/チーム） |
