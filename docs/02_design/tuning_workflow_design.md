# APIチューニングワークフロー設計

YouTube / Google Custom Search / Gemini の各APIに対して、クエリやプロンプトをチューニングするための設計。

## 1. パラメータ階層

各APIのパラメータは以下の3層で管理される。

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: CLI引数（チューニングスクリプトで変更可能）          │
│   → 試合情報、表示件数など、実行ごとに変える値              │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: 設定ファイル（settings/*.py で管理）               │
│   → クエリテンプレート、時間ウィンドウなど、チューニング対象  │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: ハードコード（src/内で固定）                       │
│   → API URL、最大取得件数など、通常変更しない値             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. YouTube Data API

### Layer 1: CLI引数

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `--home` | ホームチーム名 | Manchester City |
| `--away` | アウェイチーム名 | West Ham |
| `--kickoff-jst` | キックオフ時刻 (JST) | 翌日 00:00 |
| `--mode` | 検索カテゴリ | `all` |
| `--max-results` | 表示件数 | 10 |
| `--show-removed` | 除外動画も表示 | False |

### Layer 2: 設定ファイル (`settings/search_specs.py`)

| パラメータ | 説明 | 現在値 |
|-----------|------|-------|
| `query_template` | 検索クエリテンプレート | カテゴリ別 (下表参照) |
| `window.hours_before` | 検索開始時刻 (kickoff基準) | 48〜730日 |
| `window.offset_hours` | 検索終了時刻 (kickoff基準) | 0〜24時間 |
| `exclude_filters` | 除外キーワードリスト | `["match_highlights", ...]` |

**カテゴリ別クエリテンプレート:**

| カテゴリ | テンプレート | 時間ウィンドウ |
|---------|-------------|---------------|
| `press_conference` | `{team_name} {manager_name} press conference` | 48時間前〜kickoff |
| `historic` | `{home_team} vs {away_team} highlights` | 730日前〜24時間前 |
| `tactical` | `{team_name} 戦術 分析` | 180日前〜kickoff |
| `player_highlight` | `{player_name} {team_name} プレー` | 180日前〜kickoff |
| `training` | `{team_name} training` | 168時間前〜kickoff |

### Layer 3: ハードコード

| パラメータ | 場所 | 値 |
|-----------|------|-----|
| `API_BASE` | `youtube_client.py` | `https://www.googleapis.com/youtube/v3` |
| `FETCH_MAX_RESULTS` | `youtube_service.py` | 50 |
| `CACHE_TTL_HOURS` | `youtube_client.py` | 168 (1週間) |
| `MAX_PER_CATEGORY` | `youtube_service.py` | 10 |

---

## 3. Google Custom Search API

### Layer 1: CLI引数

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `--home` | ホームチーム名 | Manchester City |
| `--away` | アウェイチーム名 | West Ham |
| `--type` | 検索タイプ (`news`/`interview`/`all`) | `all` |
| `--save` | 結果保存先JSONファイル | なし |

### Layer 2: 設定ファイル (`settings/search_specs.py`)

| パラメータ | 説明 | 現在値 |
|-----------|------|-------|
| `query_template` | 検索クエリテンプレート | 種別ごと (下表参照) |
| `date_restrict` | 日付制限 | `d2` 〜 `d7` |
| `gl` | 地域コード | `us`, `uk`, `jp` |
| `num` | 取得件数 | 5〜10 |

**種別ごとのクエリテンプレート:**

| 種別 | テンプレート | 日付制限 |
|------|-------------|---------|
| `news` | `"{home_team}" "{away_team}" match preview -women...` | d2 |
| `interview_manager` | `"{team_name}" manager "said" OR "says"...` | d7 |
| `interview_player` | `"{team_name}" player interview "said"...` | d7 |

### Layer 3: ハードコード

| パラメータ | 場所 | 値 |
|-----------|------|-----|
| `API_URL` | `google_search_client.py` | `https://www.googleapis.com/customsearch/v1` |
| インタビュー最大件数 | `google_search_client.py` | 4件/チーム |

---

## 4. Gemini API

### Layer 1: CLI引数

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| `--home` | ホームチーム名 | Manchester City |
| `--away` | アウェイチーム名 | West Ham |
| `--mode` | モード (`summary`/`preview`/`spoiler`) | 必須 |
| `--articles-file` | 入力記事JSON | なし |
| `--text` | ネタバレチェック対象テキスト | なし |

### Layer 2: 設定ファイル

現在はプロンプトが `llm_client.py` 内にハードコードされている。
将来的に `settings/prompts.py` への外部化を検討。

| プロンプト種別 | 現在の場所 | 文字数制限 |
|--------------|-----------|-----------|
| ニュース要約 | `llm_client.py` L86-95 | 600-1000文字 |
| 戦術プレビュー | `llm_client.py` L120-130 | なし |
| ネタバレチェック | `llm_client.py` L153-165 | 入力1500文字まで |

### Layer 3: ハードコード

| パラメータ | 場所 | 値 |
|-----------|------|-----|
| `MODEL_NAME` | `llm_client.py` | `gemini-pro-latest` |

---

## 5. ディレクトリ構成

```
scripts/tuning/
├── tune_youtube.py       # YouTube検索チューニング
├── tune_news_search.py   # ニュース検索チューニング
└── tune_gemini.py        # Geminiプロンプトチューニング

settings/
├── search_specs.py       # 検索クエリ・パラメータ定義 (Layer 2)
└── channels.py           # 信頼チャンネルリスト

.agent/workflows/
└── tune-api.md           # チューニングワークフロー
```

---

## 6. ワークフロー

```bash
# Step 1: YouTube検索のチューニング
python scripts/tuning/tune_youtube.py --home "Manchester City" --away "West Ham"
# → 結果確認後、settings/search_specs.py を編集

# Step 2: ニュース検索のチューニング（結果をJSONに保存）
python scripts/tuning/tune_news_search.py --home "Manchester City" --away "West Ham" --save /tmp/articles.json
# → 結果確認後、settings/search_specs.py を編集

# Step 3: Geminiプロンプトのチューニング
python scripts/tuning/tune_gemini.py --mode summary --articles-file /tmp/articles.json
# → 出力確認後、src/clients/llm_client.py のプロンプトを編集
```
