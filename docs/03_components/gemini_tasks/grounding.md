# Grounding生成タスク (Generation with Grounding)

本ドキュメントは、GeminiのGrounding（Google検索連携）機能を使用した生成タスクの仕様を定義する。
Groundingのメカニズム詳細については [../gemini_grounding.md](../gemini_grounding.md) を参照。

> [!IMPORTANT]
> **プロンプトの単一ソース**: 本番で使用するプロンプトは [settings/gemini_prompts.py](../../../settings/gemini_prompts.py) に定義されています。本ドキュメントは概要説明のためのものであり、実装時は必ず `gemini_prompts.py` を参照してください。

---

## 1. インタビュー要約 (summarize_interview)

### 1.1 目的
監督・選手の最新コメントや記者会見の内容を検索し、要約する。

### 1.2 プロンプト仕様

**プロンプトテンプレート**: [gemini_prompts.py#interview](../../../settings/gemini_prompts.py)

**主な要件**:
- 監督の具体的な発言はカギカッコ「」で引用
- 対戦相手に対する評価やコメントを優先的に含める
- 試合結果（スコア）は絶対に含めない
- 1500-2000字程度

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
