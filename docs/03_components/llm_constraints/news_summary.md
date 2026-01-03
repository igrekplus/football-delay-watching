# ニュース要約・戦術・インタビュー仕様

本ドキュメントは、ニュース要約、戦術プレビュー生成、およびインタビュー要約機能のプロンプト仕様を定義する。
共通の制約については [llm_common.md](./llm_common.md) を参照。

## 1. generate_news_summary

**目的**: ニュース記事から試合前サマリーを生成

**現行プロンプト**:
```
Task: Summarize the following news snippets for '{home_team} vs {away_team}' into a Japanese pre-match summary (600-1000 chars).

Constraints:
- Do NOT reveal results. Check sources provided in context if needed.
- 前置き文（「はい、承知いたしました」「以下に」等のAI応答文）は絶対に含めず、本文のみを出力してください。

Context:
{context}
```

**仕様ポイント**:
- **入力**: 英語ニュース記事（Google Search API）
- **出力**: 日本語、600-1000文字
- **制約**: 結果言及禁止、AI応答文禁止

## 2. generate_tactical_preview

**目的**: 戦術分析を抽出・生成

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

**仕様ポイント**:
- **入力**: 英語ニュース記事
- **出力**: 日本語
- **制約**: フォーメーション・マッチアップにフォーカス

## 3. summarize_interview

**目的**: インタビュー記事から監督・選手のコメントを要約

**現行プロンプト**:
```
Task: {team_name}の監督が試合前に語った内容を、**可能な限り原文のまま**日本語で要約してください。

## 優先順位
1. 監督の直接発言（カギカッコ引用を最優先）
2. 選手の直接発言
3. 記事から推測されるチーム状況

## 引用ルール
- 発言は必ずカギカッコ「」で囲む
- 誰の発言かを明記（例: グアルディオラ監督は「〜」と語った）
- 英語の発言は意訳してよいが、ニュアンスを保つ

## 除外対象
- 試合結果（スコア、勝敗）
- 監督の契約・後任問題
- 女子チームの情報

## 出力形式
- 前置き文（「はい、承知いたしました」等のAI応答文）は不要、本文のみ
- 【{team_name}】のようなチーム名プレフィックスは不要（UIで表示済み）
- 1800-2000字
```

**検証方法**:
```bash
# 記事を取得
python scripts/tuning/tune_news_search.py match --home "Sunderland" --away "Manchester City" --save /tmp/articles.json

# インタビュー要約をテスト
python scripts/tuning/tune_gemini.py interview --articles-file /tmp/articles.json --home "Manchester City"
```

## 4. スポイラー判定（check_spoiler）

**目的**: 生成されたテキストがネタバレを含むか判定

**現行プロンプト**:
```
以下のテキストが「{home_team} vs {away_team}」の試合結果を言及しているかを判定してください。

テキスト:
{text[:1500]}

判定基準:
- スコア（例: 2-1, 3-0）の記載
- 勝敗の記載（例: 〇〇が勝利、敗北、won, lost）
- ゴールを決めた選手名（得点者）

回答は以下のJSON形式のみで（説明不要）:
{"is_safe": true, "reason": "なし"} または {"is_safe": false, "reason": "理由"}
```

**仕様ポイント**:
- **出力**: JSON固定 `{"is_safe": boolean, "reason": string}`
- **入力制限**: 1500文字
