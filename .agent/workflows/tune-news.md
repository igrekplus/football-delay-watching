---
description: ニュース検索のクエリをチューニングする
---

# ニュース検索チューニング

## 1. クエリを直接テスト

特定のクエリで検索結果を確認：

// turbo
```bash
python scripts/tuning/tune_news_search.py query '"Manchester City" "West Ham" preview'
```

別の例：
```bash
python scripts/tuning/tune_news_search.py query '"Arsenal" Arteta interview' --date-restrict d7 --gl uk
python scripts/tuning/tune_news_search.py query '"Liverpool" Premier League news' --num 15
```

## 2. 試合指定で自動クエリをテスト

設定ファイル (`settings/search_specs.py`) のクエリテンプレートを使用：

// turbo
```bash
python scripts/tuning/tune_news_search.py match --home "Manchester City" --away "West Ham"
```

インタビュー検索をスキップ：
```bash
python scripts/tuning/tune_news_search.py match --home "Arsenal" --away "Chelsea" --no-interview
```

## 3. 結果をJSONに保存（Geminiチューニング用）

// turbo
```bash
python scripts/tuning/tune_news_search.py match --home "Man City" --away "West Ham" --save /tmp/articles.json
```

## 4. 結果を確認して設定を編集

`settings/search_specs.py` の `GOOGLE_SEARCH_SPECS` を編集：

- **記事が少ない場合**: `date_restrict` を広げる（`d2` → `d7`）
- **関係ない記事が出る場合**: `query_template` に除外キーワードを追加（例: `-result -score`）
- **幅を広げたい場合**: `num` を増やす

## 5. 本番動作を確認

// turbo
```bash
DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```
