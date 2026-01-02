---
description: YouTube検索のクエリとフィルタをチューニングする
---

# YouTube検索チューニング

## 1. クエリを直接テスト

特定のクエリで検索結果を確認：

// turbo
```bash
python scripts/tuning/tune_youtube.py query "Manchester City training session"
```

別の例：
```bash
python scripts/tuning/tune_youtube.py query "Guardiola press conference" --days-before 14
python scripts/tuning/tune_youtube.py query "Man City vs West Ham highlights" --no-filter
```

## 2. カテゴリ別の自動クエリをテスト

設定ファイル (`settings/search_specs.py`) のクエリテンプレートを使用：

// turbo
```bash
python scripts/tuning/tune_youtube.py category training --team "Arsenal"
```

他のカテゴリ：
```bash
python scripts/tuning/tune_youtube.py category historic --home "Man City" --away "West Ham"
python scripts/tuning/tune_youtube.py category press_conference --team "Liverpool" --manager "Slot"
python scripts/tuning/tune_youtube.py category tactical --team "Chelsea"
python scripts/tuning/tune_youtube.py category player_highlight --player "Haaland" --team "Man City"
```

## 3. 結果を確認して設定を編集

- **関係ない動画が出る場合**: `settings/search_specs.py` の `exclude_filters` に除外キーワードを追加
- **結果が少ない場合**: `window` の `hours_before` / `days_before` を広げる
- **クエリが悪い場合**: `query_template` を編集

## 4. 変更後、再度テスト

// turbo
```bash
python scripts/tuning/tune_youtube.py category historic --home "Man City" --away "West Ham" --show-removed
```

## 5. 本番動作を確認

// turbo
```bash
DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```
