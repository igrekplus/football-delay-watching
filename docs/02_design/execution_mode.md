# 実行モード設計

本ドキュメントは、アプリケーションの実行モード（本番・デバッグ・モック）、環境変数、時間ウィンドウ計算、MockProviderの仕様を一元化する。

---

## 1. 環境変数一覧

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `DEBUG_MODE` | `False` | デバッグモード有効化 |
| `USE_MOCK_DATA` | `False` | モックデータ使用 |
| `USE_API_CACHE` | （自動判定） | キャッシュ有効化 |
| `CACHE_BACKEND` | `gcs` | `local` or `gcs` |
| `GCS_CACHE_BUCKET` | `football-delay-watching-cache` | GCSバケット名 |

### 環境変数の自動判定ロジック

`USE_API_CACHE` は明示的に設定されていない場合、以下のルールで自動判定される:

```python
# config.py より
if self._USE_API_CACHE_OVERRIDE is not None:
    return self._USE_API_CACHE_OVERRIDE.lower() == "true"
# Default: enable cache in debug mode with real API
return self.DEBUG_MODE and not self.USE_MOCK_DATA
```

---

## 2. モード別動作差分表

| 項目 | 本番 (Actions) | デバッグ (ローカル) | モック |
|------|---------------|-------------------|--------|
| `DEBUG_MODE` | `False` | `True` | `True` |
| `USE_MOCK_DATA` | `False` | `False` | `True` |
| `USE_API_CACHE` | `True` | `True` | `False` |
| API呼び出し | 実API | 実API | なし |
| 試合選定 | 全試合（最大3） | 1試合のみ | 固定3試合 |
| データソース | API/GCS | API/GCS | fixtures/mock_*.json |
| 出力先 | `reports/` | `reports_debug/` | `reports_mock/` |

### 実行コマンド

| モード | コマンド | 用途 |
|--------|---------|------|
| **モック** | `DEBUG_MODE=True USE_MOCK_DATA=True python main.py` | UIレイアウト確認 |
| **デバッグ** | `DEBUG_MODE=True USE_MOCK_DATA=False python main.py` | 機能の動作確認 |
| **本番** | `USE_MOCK_DATA=False python main.py` | バッチ実行 |

> [!WARNING]
> 動作確認時は原則として**デバッグモード（実API）**で実行すること。
> モックモードはUIレイアウトの確認のみに使用する。

---

## 3. 時間ウィンドウ計算

試合データの取得対象期間はモードによって異なる。

### 3.1 計算ロジック

| モード | 対象期間 |
|--------|---------|
| **本番** | `昨日 07:00 JST` ～ `今日 07:00 JST` |
| **デバッグ** | `直近土曜日 07:00 JST` ～ `翌日曜日 07:00 JST` |

### 3.2 実装詳細

```python
# config.py: TARGET_DATE プロパティ
from datetime import datetime, timedelta
import pytz

jst = pytz.timezone('Asia/Tokyo')
now_jst = datetime.now(jst)

if self.DEBUG_MODE and not self.USE_MOCK_DATA:
    # Debug mode with real API: Most recent Saturday (for testing)
    days_since_saturday = (now_jst.weekday() - 5) % 7
    if days_since_saturday == 0:
        days_since_saturday = 7  # If today is Saturday, go to last Saturday
    return now_jst - timedelta(days=days_since_saturday)
else:
    # Normal mode: yesterday
    return now_jst - timedelta(days=1)
```

### 3.3 デバッグ実行時の確認

デバッグ実行時は、対象試合の時間ウィンドウをログ等で確認すること:

```
対象時間ウィンドウ: 2025-12-28 07:00 JST ～ 2025-12-29 07:00 JST
この時間にキックオフした試合が取得されます。
```

---

## 4. MockProvider

モックモードでは `MockProvider` クラスがAPIの代わりにデータを提供する。

### 4.1 概要

| 項目 | 値 |
|------|-----|
| 実装ファイル | `src/mock_provider.py` |
| データソース | `fixtures/` ディレクトリ |
| キャッシュ | クラス内にJSONキャッシュ |

### 4.2 fixtures ディレクトリ構造

```
fixtures/
├── matches.json       # 試合一覧（固定3試合）
├── facts/
│   └── default.json   # スタメン、フォーメーション、怪我人情報
├── youtube/
│   └── default.json   # YouTube動画データ
├── news/
│   └── default.json   # ニュース記事データ
└── llm/
    └── default.json   # ニュース要約、戦術プレビュー
```

### 4.3 mock_*.json スキーマ概要

| ファイル | 主なフィールド |
|---------|--------------|
| `matches.json` | `id`, `home_team`, `away_team`, `competition`, `kickoff_jst`, `rank` |
| `facts/default.json` | `venue`, `referee`, `home_formation`, `away_formation`, `home_lineup[]`, `injuries_list[]` |
| `youtube/default.json` | `title`, `url`, `channel`, `published_at`, `thumbnail` |
| `news/default.json` | `title`, `content`, `source`, `url`, `relevance_score` |
| `llm/default.json` | `news_summary`, `tactical_preview` |

### 4.4 モックモードでの使用フロー

```mermaid
sequenceDiagram
    participant Main as main.py
    participant Cfg as config.py
    participant MP as MockProvider
    participant FS as fixtures/

    Main->>Cfg: USE_MOCK_DATA?
    Cfg-->>Main: True
    Main->>MP: get_matches()
    MP->>FS: fixtures/matches.json
    FS-->>MP: JSON data
    MP-->>Main: MatchAggregate[]
    
    Main->>MP: apply_facts(match)
    MP->>FS: fixtures/facts/default.json
    FS-->>MP: JSON data
    MP-->>Main: (in-place update)
```

---

## 5. 関連ドキュメント

- [キャッシュ設計書](./cache_design.md) - モード別キャッシュ動作
- [実行基盤設計](./infrastructure.md) - GitHub Actions、時刻処理
- [デプロイ設計書](../03_operations/deployment.md) - デプロイ手順
- [config.py](file:///Users/nagataryou/football-delay-watching/config.py) - 環境変数定義
- [src/mock_provider.py](file:///Users/nagataryou/football-delay-watching/src/mock_provider.py) - MockProvider実装

---

最終更新: 2026-01-02
