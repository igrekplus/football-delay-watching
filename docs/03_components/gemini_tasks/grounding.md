# Grounding生成タスク (Generation with Grounding)

本ドキュメントは、GeminiのGrounding（Google検索連携）機能を使用した生成タスクの仕様を定義する。
Groundingのメカニズム詳細については [../gemini_grounding.md](../gemini_grounding.md) を参照。

## 1. インタビュー要約 (summarize_interview)

### 1.1 目的
監督・選手の最新コメントや記者会見の内容を検索し、要約する。

### 1.2 プロンプト仕様

**プロンプト**:
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

### 1.3 実装ポイント
- **クライアント**: REST (`GeminiRestClient`)
- **モデル**: `gemini-2.0-flash-exp`
- **対戦相手**: 引数で指定可能（Grounding精度向上のため）
- **エラー処理**: 検索失敗時やAPIエラー時は、中途半端な生成を行わずエラーを返す。

### 1.4 検証方法
```bash
# REST API経由でのGrounding動作確認
python scripts/tuning/poc_grounding_rest.py --home "Manchester City" --away "Arsenal"
```
