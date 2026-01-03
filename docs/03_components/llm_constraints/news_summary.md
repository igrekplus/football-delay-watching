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

**目的**: インタビュー記事から監督・選手のコメントを要約（**Grounding機能使用**）

**新プロンプト (Grounding)**:
```text
Task: {team_name}の監督が、直近の試合（または次の試合）に関して語った最新のコメントや記者会見の内容を検索し、日本語で要約してください。

## 検索指示
- "{team_name} manager press conference quotes latest"
- "{team_name} vs next opponent manager quotes"
- などのクエリで最新情報を探してください。
- 直近（24-48時間以内）の情報を優先してください。

## 要約の要件
- 監督の具体的な発言があれば、可能な限りカギカッコ「」で原文のニュアンスを残して引用してください。
- 試合結果（スコアなど）が既に判明している場合は、**絶対に結果には触れず**、試合前のコメントとして構成してください。
- 確実な情報源（BBC, Sky Sports, 公式サイト等）に基づいていることを重視してください。
- **文字数: 1800-2000字程度（非常に詳細に記述してください）**

## 出力形式
- 本文のみ
```

**検証方法**:
```bash
# REST API経由でのGrounding動作確認
python scripts/tuning/poc_grounding_rest.py --home "Manchester City" --away "Arsenal"
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
