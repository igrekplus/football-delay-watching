# ユーザーユーティリティガイド (User Manual Utilities)

このドキュメントは、自動化できない（または手動確認が推奨される）「APIクォータのWeb確認」や「パラメータ算出」のためのリンク・ツール集です。

## 1. APIクォータ・ステータスのWeb確認

スクリプトによるチェックだけでなく、各サービスの公式ダッシュボードで正確な残量を確認するためのリンク集です。

| サービス | 確認すべき項目 | ダッシュボードURL |
|---|---|---|
| **API-Football** | `Account` > `My Requests` (日次リクエスト数) | [API-Sports Dashboard](https://dashboard.api-football.com/) |
| **YouTube Data API** | `Quotas` > `Queries per day` (10,000 unit/day) | [Google Cloud Console (YouTube)](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas) |
| **Google Custom Search** | `Quotas` > `Queries per day` (100 req/day) | [Google Cloud Console (Custom Search)](https://console.cloud.google.com/apis/api/customsearch.googleapis.com/quotas) |
| **Gemini API** | 課金ステータス / エラー率 | [Google AI Studio](https://aistudio.google.com/) または [Cloud Console](https://console.cloud.google.com/) |
| **Gmail API** | `Metrics` (エラーやレイテンシ) | [Google Cloud Console (Gmail)](https://console.cloud.google.com/apis/api/gmail.googleapis.com/metrics) |

### 🕒 クォータのリセットタイミング (JST)

確認時に「いつ回復するか」を知るための目安です。

- **09:00 JST**: API-Football
- **17:00 JST**: Google系 API (YouTube, Search, Gemini, Gmail)
    - ※夏時間(3月-11月)は **16:00 JST**

## 2. ヘルスチェックスクリプト（コマンド確認）

Web画面を開くのが手間な場合、API経由で現状を取得するスクリプトです。

```bash
# クォータ・ステータス一括確認
python healthcheck/check_football_api.py
python healthcheck/check_google_search.py
python healthcheck/check_gemini.py
python healthcheck/check_gmail.py
```

## 3. デバッグ対象日の手動計算（Debug Date）

デバッグ実行時に指定する「日付(TARGET_DATE)」の計算早見表です。
**「試合日」ではなく「実行日(レポート生成日)」を指定する**点に注意してください。

**計算式**: `試合日(現地) + 1日`

| 見たい試合の現地日付 | 指定する日付 (`TARGET_DATE`) |
|---|---|
| 12/23 (月) | **12/24** |
| 12/24 (火) | **12/25** |
| 12/26 (木) | **12/27** |
| 12/28 (土) | **12/29** |

---
※ 開発フロー・デプロイ手順などの詳細については [GEMINI.md](../GEMINI.md) を参照してください。
