# Gemini Grounding (Google Search) 仕様

本ドキュメントは、Gemini APIのGrounding機能（Google Search連携）に関する技術仕様と実装詳細を定義する。

## 1. 概要

### 1.1 目的
最新のWeb情報をLLMに取り込み、情報の鮮度と正確性を向上させる。特に、**試合前インタビューの引用**において、正確な発言内容を検索・引用するために使用する。

### 1.2 技術スタック
- **API**: Gemini API (REST)
- **Model**: `gemini-2.0-flash-exp` (※Grounding機能が安定しているバージョン)
- **Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
- **Tool**: `googleSearch`

> [!NOTE]
> `google-generativeai` Python SDKの一部バージョンではGrounding機能が不安定なため、`src/clients/gemini_rest_client.py` 経由でREST APIを直接使用する。

---

## 2. 実装詳細

### 2.1 GeminiRestClient
Grounding機能専用の軽量RESTクライアント。

- **リトライポリシー**: 
    - タイムアウトや500系エラー時：最大2回リトライ（計3回試行）
    - 400系（Bad Request）：リトライせず即時エラー
- **Grounding Metadata**:
    - レスポンスに含まれる `groundingMetadata` をログに出力（デバッグ用）

### 2.2 プロンプト設計（検索指示）
Groundingを有効にする場合、プロンプト内に明確な「検索指示」を含めることが推奨される。

**例:**
```text
Task: ...

## 検索指示
- "{team_name} manager press conference quotes latest"
- "{team_name} vs {opponent} manager quotes"
- などのクエリで最新情報を探してください。
- 直近（24-48時間以内）の情報を優先してください。
```

---

## 3. エラーハンドリング

### 3.1 フォールバックなし
Grounding機能が必須のタスク（インタビュー要約等）においてAPIエラーが発生した場合、中途半端な推測生成を行わず、**「取得エラー」として処理を中断**する。

**戻り値:**
`"エラーにつき取得不可（情報の取得に失敗しました）"`

### 3.2 ログ出力
エラー時は必ず `logger.error` で詳細を出力する。
- Error Type
- Status Code
- Response Body (if available)

---

## 4. 制限事項（Quota）
- Gemini APIのRate Limitに準拠する。
- Grounding機能は別途Google Searchのクォータを消費する可能性がある（契約形態による）。現状はFree Tier範囲内で運用。

---

## 5. 関連ドキュメント
## 5. 関連ドキュメント
- [generation.md](./gemini_tasks/generation.md) - プロンプト詳細
- [grounding.md](./gemini_tasks/grounding.md) - Groundingプロンプト詳細
- [common.md](./gemini_tasks/common.md) - LLM共通制約
