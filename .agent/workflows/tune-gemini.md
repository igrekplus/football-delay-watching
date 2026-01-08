---
description: Geminiプロンプトをチューニングする
---

# Geminiプロンプトチューニング

> [!IMPORTANT]
> **⚠️ 重要: 品質の評価とログ記録について**
> 1. **品質評価はユーザーの責務**: AIは結果の品質（例：「良い要約」「正確なプレビュー」等）を評価しては**いけません**。品質を判断できるのはユーザーだけです。AIの役割はテストを実行し、生の出力を提示することに徹してください。
> 2. **ログ記録は必須**: 実行ごとに、リクエストとレスポンスの完全なペアをログファイルに保存する必要があります。
>    - **パス**: `/temp/tuning/yyyy-mm-dd-hhmmdd_gemini_tuning.md`
>    - **フォーマット**:
>      ```markdown
>      # Run: yyyy-mm-dd hh:mm:ss
>      ## Command
>      `{command}`
>      ## Output
>      {raw_output}
>      ```

## 事前準備: 記事データを取得

まずニュース検索で記事を取得し、JSONに保存：

// turbo
```bash
python scripts/tuning/tune_news_search.py match --home "Man City" --away "West Ham" --save /tmp/articles.json
```

## 1. ニュース要約をテスト

// turbo
```bash
python scripts/tuning/tune_gemini.py summary --articles-file /tmp/articles.json --home "Man City" --away "West Ham"
```

確認ポイント：
- 適切な長さか（600-1000文字）
- ネタバレを含んでいないか
- 前置き文（「はい、承知しました」等）がないか

## 2. 戦術プレビューをテスト

> ⚠️ 現在、いない選手を含む妄想が生成される問題あり

// turbo
```bash
python scripts/tuning/tune_gemini.py preview --articles-file /tmp/articles.json --home "Man City" --away "West Ham"
```

確認ポイント：
- 記事に記載された情報のみを使用しているか
- いない選手を含んでいないか
- 創作・妄想を含んでいないか

## 3. ネタバレチェックをテスト

// turbo
```bash
python scripts/tuning/tune_gemini.py spoiler --text "City won 3-1 with Haaland scoring twice" --home "Man City" --away "West Ham"
```

安全なテキスト：
```bash
python scripts/tuning/tune_gemini.py spoiler --text "Man City and West Ham will face each other this weekend" --home "Man City" --away "West Ham"
```

## 4. プロンプトを編集

`settings/gemini_prompts.py` を編集：

| プロンプト種別 | key | 修正内容 |
|---------|-------|---------| 
| ニュース要約 | `news_summary` | 要約プロンプト |
| 戦術プレビュー | `tactical_preview` | 戦術分析プロンプト |
| ネタバレ判定 | `check_spoiler` | ネタバレ判定プロンプト |
| インタビュー | `interview` | 監督インタビュー要約 |
| 同国対決 | `same_country_trivia` | トリビア生成 |

> [!TIP]
> プロンプトはテンプレート変数（`{home_team}`等）を使用できます。`build_prompt()` 関数で展開されます。

## 5. 変更後、再度テスト

// turbo
```bash
python scripts/tuning/tune_gemini.py summary --articles-file /tmp/articles.json --home "Man City" --away "West Ham"
```

## 6. 本番動作を確認

// turbo
```bash
DEBUG_MODE=True USE_MOCK_DATA=False python main.py
```
