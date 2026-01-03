---
description: YouTube検索のクエリとフィルタをチューニングする
---

# YouTube検索チューニング

> [!IMPORTANT]
> **⚠️ CRITICAL: Quality Evaluation & Logging**
> 1. **User Evaluates Quality**: AI MUST NOT evaluate the quality of the results (e.g., "relevant videos", "good channels"). ONLY the user can judge quality. The AI's role is to run the test and present the raw output.
> 2. **Mandatory Logging**: You MUST save the full Request/Response pair to a log file for every run.
>    - **Path**: `/temp/tuning/yyyy-mm-dd-hhmmdd_youtube_tuning.md`
>    - **Format**:
>      ```markdown
>      # Run: yyyy-mm-dd hh:mm:ss
>      ## Command
>      `{command}`
>      ## Output
>      {raw_output}
>      ```

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
