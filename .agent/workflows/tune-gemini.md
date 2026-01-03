---
description: Geminiプロンプトをチューニングする
---

# Geminiプロンプトチューニング

> [!IMPORTANT]
> **⚠️ CRITICAL: Quality Evaluation & Logging**
> 1. **User Evaluates Quality**: AI MUST NOT evaluate the quality of the results (e.g., "good summary", "accurate preview"). ONLY the user can judge quality. The AI's role is to run the test and present the raw output.
> 2. **Mandatory Logging**: You MUST save the full Request/Response pair to a log file for every run.
>    - **Path**: `/temp/tuning/yyyy-mm-dd-hhmmdd_gemini_tuning.md`
>    - **Format**:
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

`src/clients/llm_client.py` を編集：

| メソッド | 行番号 | 修正内容 |
|---------|-------|---------|
| `generate_news_summary` | L86-95 | 要約プロンプト |
| `generate_tactical_preview` | L120-130 | 戦術プレビュープロンプト |
| `check_spoiler` | L153-165 | ネタバレ判定プロンプト |

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
