# Gemini Content Filtering 仕様

本ドキュメントは、Gemini APIを使用したコンテンツフィルタリング（Post-Filter）に関する技術仕様と実装詳細を定義する。

## 1. 概要

### 1.1 目的
従来のキーワードベースのフィルタでは除去しきれない、「文脈的に不適切なコンテンツ」をLLMの理解力を用いてフィルタリングする。

### 1.2 主なユースケース
- **因縁（Historic Clashes）検索**: "Liverpool vs Leeds" を検索しても、"Man Utd vs Leeds" や一般的な "Premier League Rivalries" など、当該2チーム間の対戦に特化していない動画が混入する問題を解決する (Issue #109)。

### 1.3 技術スタック
- **API**: Gemini API (REST)
- **Model**: `gemini-2.0-flash-exp` (高速・低コスト)
- **Client**: `GeminiRestClient` (拡張実装)

---

## 2. アーキテクチャ

### 2.1 コンポーネント構成
`YouTubePostFilter` が `GeminiRestClient` を利用して判断を行う。

```mermaid
graph LR
    A[YouTubeService] --> B[YouTubePostFilter]
    B -->|候補リスト & 条件| C[GeminiRestClient]
    C -->|判定結果 (JSON)| B
    B -->|フィルタ済みリスト| A
```

### 2.2 処理フロー
1. **候補抽出**: APIから検索結果（約50件）を取得。
2. **ルールベースフィルタ**: 既存の `filter_match_highlights` 等で明らかに不要なものを除去。
3. **LLMフィルタ (Optional)**: 残った候補に対して、Geminiに判定を依頼。
    - 入力: 動画タイトル、チャンネル名、説明（冒頭）
    - 指示: 「チームAとチームBの直接対決、または関係性に関する動画以外を除外せよ」
4. **最終選定**: LLMが「適合」と判定したもののみを採用。

---

## 3. プロンプト設計

### 3.1 因縁フィルタ用プロンプト

**Input Format:**
```json
[
  {"id": 0, "title": "Liverpool vs Leeds 4-3", "channel": "LFC"},
  {"id": 1, "title": "Man Utd vs Leeds Rivalry", "channel": "Sky Sports"}
]
```

**Instruction:**
- 指定された2チーム（{home_team} vs {away_team}）の対戦、または両チーム間の歴史的因縁に**直接関連する**動画のみを選んでください。
- 他のチームとの対戦（例: {home_team} vs Other）は除外してください。
- リーグ全体の汎用的な動画も、両チームにフォーカスしていなければ除外してください。

**Output Format:**
```json
{
  "kept_indices": [0],
  "reasoning": "Video 1 is about Man Utd."
}
```

---

## 4. エラーハンドリング

### 4.1 フォールバック
Gemini APIがエラー（タイムアウト、500エラー）を返した場合、**フィルタリングを行わず（フェイルセーフ）、ルールベースフィルタの結果をそのまま採用する**か、または**保守的に上位数件のみ採用する**。
- **現状の戦略**: エラー時はログを出力し、LLMフィルタをスキップする（全件採用＝過剰除去よりは混入を許容）。

### 4.2 コスト・レイテンシ考慮
- 全検索に対して行うとコスト・時間がかかるため、**「因縁」など精度が特に低いカテゴリに限定**して適用する。
- 一度のプロンプトで複数件（最大50件）をバッチ判定させる。
