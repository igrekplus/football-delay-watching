# APIチューニングワークフロー設計

YouTube / Gemini (Grounding) / Google Custom Search (Legacy) の各APIに対して、クエリやプロンプトをチューニングするための設計。

## 1. 背景と課題

### 現状の問題

| 領域 | 問題 | 原因 |
|-----|------|------|
| YouTube (因縁) | 別チームのハイライトが出る | クエリが曖昧 / フィルタ不足 |
| YouTube (記者会見) | 結果が見つからない | クエリが厳しすぎる |
| ニュース検索 | 記事が少ない・幅が狭い | 検索範囲が狭い |
| 戦術プレビュー | いない選手を含む妄想 | プロンプトがAPIデータを強制していない |

### チューニングの目的

- **デバッグモードを回さずに**、個別APIの結果を確認・調整する
- **高速な反復**：クエリ変更 → 結果確認 → 改善 のサイクルを素早く回す

---

## 2. パラメータ階層

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: CLI引数（チューニングスクリプトで変更可能）          │
│   → クエリ文字列、チーム名、日付、表示件数など               │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: 設定ファイル（settings/*.py）                      │
│   → クエリテンプレート、時間ウィンドウ、除外フィルタ         │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: ハードコード（src/内で固定）                       │
│   → API URL、キャッシュTTL、最大取得件数                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. YouTube チューニング (`tune_youtube.py`)

### サブコマンド

#### `query` - クエリを直接テスト

```bash
python scripts/tuning/tune_youtube.py query "Manchester City training session"
python scripts/tuning/tune_youtube.py query "Guardiola press conference" --days-before 7
```

| 引数 | 説明 | デフォルト |
|-----|------|-----------|
| `QUERY` | 検索クエリ（必須） | - |
| `--days-before` | 何日前から検索 | 7 |
| `--max-results` | 表示件数 | 20 |
| `--no-filter` | フィルタを適用しない | False |

#### `category` - カテゴリ別の自動クエリをテスト

```bash
python scripts/tuning/tune_youtube.py category historic --home "Man City" --away "West Ham"
python scripts/tuning/tune_youtube.py category training --team "Arsenal"
```

| 引数 | 説明 | デフォルト |
|-----|------|-----------|
| `CATEGORY` | `press_conference`, `historic`, `tactical`, `player_highlight`, `training` | 必須 |
| `--home` | ホームチーム | - |
| `--away` | アウェイチーム | - |
| `--team` | チーム名（単体検索用） | - |
| `--kickoff-jst` | キックオフJST | 翌日 00:00 |

#### `filter` - フィルタロジックをテスト

```bash
python scripts/tuning/tune_youtube.py filter --input results.json
```

### 出力形式

```
================================================================================
QUERY: Manchester City vs West Ham highlights
PARAMS: published_after=2024-01-01, published_before=2026-01-02, max_results=20
================================================================================
RAW API RESULTS (10 件):

1. [✅ KEPT] Man City 4-0 West Ham | Extended Highlights
   Channel: Premier League (✓ trusted)
   URL: https://youtube.com/watch?v=xxx
   Published: 2025-12-15

2. [❌ REMOVED: contains "reaction"] West Ham fans REACT to loss
   Channel: Random Fan Channel
   URL: https://youtube.com/watch?v=yyy

3. [❌ REMOVED: wrong teams detected] Liverpool vs Arsenal
   Channel: Premier League (✓ trusted)
   URL: https://youtube.com/watch?v=zzz

================================================================================
SUMMARY: KEPT=5 | REMOVED=5
================================================================================
Tip: フィルタを調整するには settings/search_specs.py の exclude_filters を編集
```

---

## 4. ニュース検索チューニング (`tune_news_search.py`)

> [!WARNING]
> 本ツールは **Legacy (旧Google Custom Search)** 用です。
> 現在、ニュース検索はGemini Groundingに移行済みのため、本ツールの使用は推奨されません。
> Groundingのプロンプト調整には `tune_gemini.py` を使用してください。

### サブコマンド

#### `query` - クエリを直接テスト

```bash
python scripts/tuning/tune_news_search.py query '"Manchester City" "West Ham" preview'
python scripts/tuning/tune_news_search.py query '"Arsenal" Arteta interview' --date-restrict d7
```

| 引数 | 説明 | デフォルト |
|-----|------|-----------|
| `QUERY` | 検索クエリ（必須） | - |
| `--date-restrict` | 日付制限 (`d1`, `d2`, `d7`, `w1`) | `d2` |
| `--gl` | 地域コード | `us` |
| `--num` | 取得件数 | 10 |

#### `match` - 試合指定で自動クエリをテスト

```bash
python scripts/tuning/tune_news_search.py match --home "Man City" --away "West Ham"
python scripts/tuning/tune_news_search.py match --home "Arsenal" --away "Chelsea" --save articles.json
```

| 引数 | 説明 | デフォルト |
|-----|------|-----------|
| `--home` | ホームチーム（必須） | - |
| `--away` | アウェイチーム（必須） | - |
| `--save` | 結果をJSONに保存 | - |

### 出力形式

```
================================================================================
QUERY: "Manchester City" "West Ham" match preview -women -WFC -WSL -女子
PARAMS: dateRestrict=d2, gl=us, num=10
================================================================================
RESULTS (6 件):

1. [relevance=2] Man City vs West Ham: Preview and Predictions
   Source: theguardian.com
   URL: https://...
   Snippet: Manchester City host West Ham at the Etihad Stadium...

2. [relevance=1] Premier League Weekend Preview
   Source: skysports.com
   ...

================================================================================
Tip: クエリを変更するには settings/search_specs.py の GOOGLE_SEARCH_SPECS を編集
```

---

## 5. Gemini チューニング (`tune_gemini.py`)

### サブコマンド

#### `summary` - ニュース要約をテスト

```bash
python scripts/tuning/tune_gemini.py summary --articles-file articles.json --home "Man City" --away "West Ham"
```

#### `preview` - 戦術プレビューをテスト

```bash
python scripts/tuning/tune_gemini.py preview --articles-file articles.json --home "Man City" --away "West Ham"
```

> [!WARNING]
> 戦術プレビューは現在「いない選手を含む妄想」が生成される問題あり。
> プロンプトに「記事に記載された情報のみを使用せよ」を強制する必要がある。

#### `spoiler` - ネタバレチェックをテスト

```bash
python scripts/tuning/tune_gemini.py spoiler --text "City won 3-1" --home "Man City" --away "West Ham"
```

### 出力形式 (summary)

```
================================================================================
GEMINI SUMMARY | Manchester City vs West Ham
================================================================================
Input: 6 articles from articles.json
Prompt:
  Task: Summarize the following news snippets...
  Constraints: Do NOT reveal results...

--- Generated Output ---
今週末のマンチェスター・シティ対ウエストハム戦は注目の一戦となる。
シティは直近5試合で4勝1分と好調を維持...
(800文字)
--- End ---

================================================================================
Tip: プロンプトを変更するには src/clients/llm_client.py を編集
```

---

## 6. ディレクトリ構成

```
scripts/tuning/
├── __init__.py
├── tune_youtube.py
├── tune_news_search.py
└── tune_gemini.py

.agent/workflows/
├── tune-youtube.md      # YouTubeチューニング手順
├── tune-news.md         # ニュース検索チューニング手順
└── tune-gemini.md       # Geminiプロンプトチューニング手順
```

---

## 7. ワークフロー概要

### YouTube チューニング (`/tune-youtube`)

1. `query` でクエリを直接試す
2. 結果を見て `settings/search_specs.py` を編集
3. `category` で自動生成クエリを確認
4. デバッグモードで本番動作を確認

### ニュース検索チューニング (`/tune-news`)

1. `query` でクエリを直接試す
2. `--save` で結果をJSONに保存（Geminiチューニング用）
3. `settings/search_specs.py` を編集

### Gemini チューニング (`/tune-gemini`)

1. ニュース検索で保存したJSONを入力
2. `summary` / `preview` で生成結果を確認
3. `src/clients/llm_client.py` のプロンプトを編集
