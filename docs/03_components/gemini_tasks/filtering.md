# フィルタリングタスク (Content Filtering)

本ドキュメントは、検索結果などの外部データに対するフィルタリングタスクの仕様を定義する。

## 1. YouTube Post-Filter

### 1.1 目的
従来のキーワードベースのフィルタでは除去しきれない、「文脈的に不適切なコンテンツ」をLLMの理解力を用いてフィルタリングする。
特に「因縁（Historic Clashes）」検索における無関係な動画の混入を防ぐ。

### 1.2 アーキテクチャ
`YouTubePostFilter` が `GeminiRestClient` を利用して判断を行う。

```mermaid
graph LR
    A[YouTubeService] --> B[YouTubePostFilter]
    B -->|候補リスト & 条件| C[GeminiRestClient]
    C -->|判定結果 (JSON)| B
    B -->|フィルタ済みリスト| A
```

### 1.3 プロンプト仕様

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

### 1.4 実装ポイント
- **クライアント**: REST (`GeminiRestClient`)
- **モデル**: `gemini-2.0-flash-exp` (高速・低コスト)
- **フェイルセーフ**: APIエラー時はフィルタリングを行わず、ルールベースの結果を採用する（安全側に倒す）。
- **バッチ処理**: 一度のプロンプトで複数件（最大50件）をまとめて判定させ、コストとレイテンシを抑制する。
