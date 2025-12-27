# YouTube動画取得ロジック仕様書

> **Last Updated**: 2025-12-28  
> **Source of Truth**: `src/youtube_service.py`, `src/youtube_filter.py`

## 概要

試合レポートに含めるYouTube動画を取得するロジック。
**キックオフ前の動画のみを対象**とし、試合結果のネタバレを防ぐ。

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    YouTubeService                           │
├─────────────────────────────────────────────────────────────┤
│  get_videos_for_match(match)                                │
│    ├─ _search_press_conference() × 2チーム                  │
│    │    └─ filter.exclude_highlights() + filter.sort_trusted()
│    ├─ _search_historic_clashes() × 1                        │
│    │    └─ filter.sort_trusted() のみ（ハイライト除外なし）  │
│    ├─ _search_tactical() × 2チーム                          │
│    │    └─ filter.exclude_highlights() + filter.sort_trusted()
│    ├─ _search_player_highlight() × 6選手                    │
│    │    └─ filter.exclude_highlights() + filter.sort_trusted()
│    ├─ _search_training() × 2チーム                          │
│    │    └─ filter.exclude_highlights() + filter.sort_trusted()
│    └─ filter.deduplicate() ← 最後に全結果を統合             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 YouTubePostFilter (新規)                    │
├─────────────────────────────────────────────────────────────┤
│  exclude_highlights(videos) → 試合ハイライト/ライブ等を除外 │
│  sort_trusted(videos)       → 信頼チャンネル優先ソート     │
│  deduplicate(videos)        → 重複排除（video_id ベース）  │
└─────────────────────────────────────────────────────────────┘
```

---

## パラメータ一覧

| パラメータ名 | デフォルト値 | 対応メソッド | 説明 |
|-------------|-------------|-------------|------|
| `PRESS_CONFERENCE_SEARCH_HOURS` | **48** | `_search_press_conference()` | 記者会見検索期間 |
| `HISTORIC_SEARCH_DAYS` | **730**（2年） | `_search_historic_clashes()` | 過去ハイライト検索期間 |
| `TACTICAL_SEARCH_DAYS` | **180**（6ヶ月） | `_search_tactical()` | 戦術分析検索期間 |
| `PLAYER_SEARCH_DAYS` | **180**（6ヶ月） | `_search_player_highlight()` | 選手紹介検索期間 |
| `TRAINING_SEARCH_HOURS` | **168**（1週間） | `_search_training()` | 練習動画検索期間 |
| `FETCH_MAX_RESULTS` | **50** | 全メソッド | 取得件数（post-filter前） |

---

## YouTubePostFilter クラス設計

### ファイル: `src/youtube_filter.py` (新規)

```python
class YouTubePostFilter:
    """YouTube動画のpost-filterを提供するクラス"""
    
    def exclude_highlights(self, videos: List[Dict]) -> Dict[str, List[Dict]]:
        """試合ハイライト/フルマッチ/ライブ配信を除外"""
        # returns {"kept": [...], "removed": [...]}
    
    def sort_trusted(self, videos: List[Dict]) -> List[Dict]:
        """信頼チャンネル優先でソート"""
    
    def deduplicate(self, videos: List[Dict]) -> List[Dict]:
        """重複排除（video_id ベース）"""
```

### 各検索メソッドでのフィルター適用

| カテゴリ | `exclude_highlights()` | `sort_trusted()` | `deduplicate()` |
|---------|:---------------------:|:----------------:|:---------------:|
| 記者会見 | ✅ | ✅ | - |
| 過去対戦 | ❌（クエリがhighlights含む） | ✅ | - |
| 戦術分析 | ✅ | ✅ | - |
| 選手紹介 | ✅ | ✅ | - |
| 練習風景 | ✅ | ✅ | - |
| **全体** | - | - | ✅（最後に1回） |

---

## 動画カテゴリ別仕様

### カテゴリ1: 記者会見 (`press_conference`)

| 項目 | 値 |
|------|-----|
| メソッド | `_search_press_conference()` |
| クエリ | `{team} {manager_name} press conference` |
| クエリ数 | **2クエリ/試合**（1クエリ × 2チーム） |
| 検索期間 | キックオフ - 48時間 ～ キックオフ |
| maxResults | **50** |
| フィルタ | `exclude_highlights()` + `sort_trusted()` |

> **Note**: 監督名がない場合は `{team} press conference`

---

### カテゴリ2: 過去対戦ハイライト (`historic`)

| 項目 | 値 |
|------|-----|
| メソッド | `_search_historic_clashes()` |
| クエリ | `{home} vs {away} highlights` |
| クエリ数 | **1クエリ/試合** |
| 検索期間 | キックオフ - 730日 ～ キックオフ |
| maxResults | **50** |
| フィルタ | `sort_trusted()` のみ |

> **Note**: クエリ自体が `highlights` を含むため、ハイライト除外フィルタは適用しない

---

### カテゴリ3: 戦術分析 (`tactical`)

| 項目 | 値 |
|------|-----|
| メソッド | `_search_tactical()` |
| クエリ | `{team} 戦術 分析` **（日本語固定）** |
| クエリ数 | **2クエリ/試合**（1クエリ × 2チーム） |
| 検索期間 | キックオフ - 180日 ～ キックオフ |
| maxResults | **50** |
| フィルタ | `exclude_highlights()` + `sort_trusted()` |

---

### カテゴリ4: 選手紹介 (`player_highlight`)

| 項目 | 値 |
|------|-----|
| メソッド | `_search_player_highlight()` |
| クエリ | `{player_name} {team_name} プレー` **（日本語固定）** |
| クエリ数 | **6クエリ/試合**（3選手 × 2チーム）、デバッグ: 2クエリ |
| 検索期間 | キックオフ - 180日 ～ キックオフ |
| maxResults | **50** |
| フィルタ | `exclude_highlights()` + `sort_trusted()` |

#### 選手選択ロジック

```python
# スタメンリストの末尾（FW想定）から優先
player_count = 1 if DEBUG_MODE else 3
for player in reversed(match.home_lineup):
    if len(home_players) < player_count:
        home_players.append(player)
```

---

### カテゴリ5: 練習風景 (`training`)

| 項目 | 値 |
|------|-----|
| メソッド | `_search_training()` |
| クエリ | `{team} training` **（英語固定）** |
| クエリ数 | **2クエリ/試合**（1クエリ × 2チーム） |
| 検索期間 | キックオフ - 168時間（1週間） ～ キックオフ |
| maxResults | **50** |
| フィルタ | `exclude_highlights()` + `sort_trusted()` |

---

## 処理フロー

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 検索（カテゴリ別）                                  │
│   YouTubeService._search_videos()                           │
│   ├─ キャッシュチェック（HIT ならAPI呼び出しスキップ）      │
│   ├─ YouTube Data API search.list 呼び出し                  │
│   └─ 結果をキャッシュに保存                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: フィルター適用（カテゴリ別）                        │
│   YouTubePostFilter を使用                                  │
│   ├─ filter.exclude_highlights()  ... 過去対戦以外で適用   │
│   └─ filter.sort_trusted()        ... 全カテゴリで適用     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 集約・重複排除（全カテゴリ統合後）                  │
│   filter.deduplicate()                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## exclude_highlights() ルール

`YouTubePostFilter.exclude_highlights()` で適用されるルール。

**適用カテゴリ**: 記者会見、戦術分析、選手紹介、練習風景  
**除外カテゴリ**: 過去対戦ハイライト（クエリ自体が `highlights` を含むため）

| ルール名 | 除外キーワード | 説明 |
|---------|---------------|------|
| `match_highlights_vs` | `highlights` + (`vs` or `v` or `vs.`) | 試合ハイライト（対戦形式） |
| `match_highlights` | `match highlights`, `extended highlights` | 試合ハイライト（単独） |
| `highlights` | `highlights` | 単独の「highlights」 |
| `full_match` | `full match`, `full game`, `full replay` | フルマッチ |
| `live_stream` | `live`, `livestream`, `watch live`, `streaming` | ライブ配信 |
| `matchday` | `matchday` | マッチデー |
| `press_conference` | `press conference` | 記者会見（選手紹介向け） |
| `reaction` | `reaction` | リアクション動画 |

> **Note**: フィルタはタイトル + 説明文に対して適用（小文字変換後）

---

## 信頼チャンネル管理

### ファイル構成

```
settings/channels.py
├─ TRUSTED_CHANNELS: Dict[str, Dict]  # チャンネルID → メタデータ
├─ is_trusted_channel(channel_id)     # 判定関数
├─ get_channel_info(channel_id)       # メタデータ取得
└─ get_channel_display_name(...)      # 表示名取得
```

### TRUSTED_CHANNELS 構造

```python
TRUSTED_CHANNELS = {
    "UCkzCjdRMrW2vXLx8mvPVLdQ": {
        "name": "Man City",
        "handle": "@mancity",
        "category": "team",
    },
    # ...
}
```

### カテゴリ一覧

| category | 説明 | 例 |
|----------|------|-----|
| `team` | クラブ公式 | Man City, Arsenal, Liverpool |
| `league` | リーグ公式 | Premier League, La Liga |
| `broadcaster` | 放送局 | Sky Sports, DAZN, TNT Sports |
| `tactics` | 戦術分析 | Tifo Football, レオザフットボール |
| `media` | メディア | スポルティーバ, PIVOT |

---

## ソートロジック

```python
# 信頼チャンネル優先、その中ではrelevance順維持
videos.sort(key=lambda v: (
    0 if v["is_trusted"] else 1,  # 信頼チャンネル優先
    v.get("original_index", 0)     # relevance順を維持
))
```

---

## キャッシュ

| 項目 | 値 |
|------|-----|
| TTL | **168時間（1週間）** |
| 保存先 | `api_cache/youtube/{cache_key}.json` |
| キーの構成 | `query + relevance_language + region_code + channel_id + publishedAfter + publishedBefore` → MD5 |
| 有効化 | `config.USE_API_CACHE` または `cache_enabled` 引数 |

---

## APIクォータ

| 項目 | 値 |
|------|-----|
| 無料枠 | 10,000ユニット/日 |
| search.list | **100ユニット/リクエスト** |
| リセット時間 | 太平洋時間 0:00（JST 17:00） |

### 1試合あたりのコスト

| カテゴリ | クエリ数 | ユニット |
|---------|----------|----------|
| 記者会見 | 2 | 200 |
| 過去対戦ハイライト | 1 | 100 |
| 戦術分析 | 2 | 200 |
| 選手紹介 | 6（デバッグ: 2） | 600（200） |
| 練習風景 | 2 | 200 |
| **合計（通常）** | **13** | **1,300** |
| **合計（デバッグ）** | **9** | **900** |

---

## 公開API（healthcheck用）

| メソッド | 用途 |
|---------|------|
| `search_videos_raw(...)` | 生検索（フィルタなし） |
| `apply_trusted_channel_sort(videos)` | 信頼チャンネル優先ソート |
| `apply_player_post_filter(videos)` | 選手post-filter |
| `search_training_videos(team, kickoff, max_results)` | 練習動画検索 |
| `search_player_videos(player, team, kickoff, max_results, apply_post_filter)` | 選手動画検索 |

---

## レポート出力形式

```html
<details>
<summary><strong>🎤 記者会見 (3件)</strong></summary>
<table class="youtube-table">
<thead><tr><th>サムネイル</th><th>動画情報</th></tr></thead>
<tbody>
<tr>
  <td><a href="..."><img src="..." style="width:120px;height:auto;"></a></td>
  <td><strong><a href="...">Title...</a></strong><br/>
      📺 <strong>✅ Man City</strong> ・ 🕐 2日前<br/>
      <em>Description...</em></td>
</tr>
</tbody>
</table>
</details>
```

- **✅**: 信頼チャンネル（TRUSTED_CHANNELS登録済み）
- **⚠️**: 非信頼チャンネル（要確認）

---

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-12-28 | 全カテゴリ maxResults を 50 に拡張（Issue #45, #46対応） |
| 2025-12-28 | ハイライト除外post-filterを全カテゴリに適用（過去対戦除く） |
| 2025-12-27 | 選手クエリを `{player} {team} プレー` に変更 |
| 2025-12-27 | 選手紹介 maxResults を 50 に拡張 + post-filter追加 |
| 2025-12-27 | 練習動画検索期間を168時間（1週間）に延長 |
| 2025-12-27 | 公開API追加（`search_training_videos`, `search_player_videos`） |
| 2025-12-27 | ヘルスチェックスクリプトのリファクタリング |
| 2025-12-24 | Issue #27: クエリ削減（20→13）、post-fetchフィルタ方式実装 |
| 2025-12-24 | キャッシュTTL 24時間→1週間に変更 |
| 2025-12-24 | 選手紹介カテゴリを戦術から分離 |
