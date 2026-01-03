# 汎用生成タスク (Standard Generation)

本ドキュメントは、Grounding（Google検索）を使用しない、標準的なテキスト生成タスクの仕様を定義する。
共通の制約については [common.md](./common.md) を参照。

## 1. ニュース要約 (generate_news_summary)

### 1.1 目的
ニュース記事（検索結果）から試合前サマリーを生成する。

### 1.2 プロンプト仕様

**現行プロンプト**:
```
Task: Summarize the following news snippets for '{home_team} vs {away_team}' into a Japanese pre-match summary (600-1000 chars).

Constraints:
- Do NOT reveal results. Check sources provided in context if needed.
- 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。

Context:
{context}
```

### 1.3 実装ポイント
- **クライアント**: SDK (`google-generativeai`)
- **モデル**: `gemini-pro-latest`
- **入力**: 英語ニュース記事 text (Google Search API結果)
- **出力**: 日本語、600-1000文字
- **制約**: 結果言及禁止、AI応答文禁止

---

## 2. 戦術プレビュー (generate_tactical_preview)

### 2.1 目的
戦術分析記事から見どころを抽出し、プレビューを生成する。

### 2.2 プロンプト仕様

**現行プロンプト**:
```
Task: Extract tactical analysis for '{home_team} vs {away_team}' (Japanese).

Constraints:
- Focus on likely formations and matchups. Do NOT reveal results.
- 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。
- 最初の一文から戦術分析の内容を開始してください。

Context:
{context}
```

### 2.3 実装ポイント
- **クライアント**: REST (`GeminiRestClient`) ※Grounding移行予定または統一のためREST使用の場合あり
- **モデル**: `gemini-2.0-flash-exp` (推奨)
- **出力**: 日本語
- **制約**: フォーメーション・マッチアップにフォーカス
